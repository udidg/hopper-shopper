"""LLM service – Gemini (primary) + Ollama (fallback) for grocery list features.

Provides:
- Department classification (single + batch)
- Smart item parsing (extract quantity, unit, brand)
- Natural language intent understanding
- JSON extraction utilities
- In-memory result caching
- Global rate limiting (configurable, default 20 req/min)

Backend priority:
1. Gemini API (cloud, stronger model) — if GEMINI_API_KEY is set
2. Ollama (local, lighter model) — if OLLAMA_URL is set and reachable
3. None — graceful degradation to keyword-only matching
"""

import asyncio
import json
import logging
import re
import time
from collections import deque
from typing import Optional

import httpx

from bot.config import settings
from bot.services.grouping import (
    DEPARTMENTS_EN,
    DEPARTMENTS_HE,
    DEPT_EN_TO_HE,
    is_hebrew,
)

logger = logging.getLogger(__name__)

# ── Timeouts ─────────────────────────────────────────────────────

_OLLAMA_TIMEOUT = 15.0
_OLLAMA_BATCH_TIMEOUT = 30.0
_GEMINI_TIMEOUT = 15.0
_GEMINI_BATCH_TIMEOUT = 30.0

# ── Global rate limiter (sliding window) ─────────────────────────

_rate_limit_lock = asyncio.Lock()
_request_timestamps: deque[float] = deque()


async def _acquire_rate_limit() -> bool:
    """Check and acquire a slot in the global rate limiter.

    Returns True if the request is allowed, False if rate limit exceeded.
    Uses a sliding window of 60 seconds.
    """
    async with _rate_limit_lock:
        now = time.monotonic()
        window = 60.0  # 1 minute

        # Purge timestamps older than the window
        while _request_timestamps and _request_timestamps[0] < now - window:
            _request_timestamps.popleft()

        if len(_request_timestamps) >= settings.llm_rate_limit:
            logger.warning(
                "LLM rate limit reached (%d/%d req/min)",
                len(_request_timestamps),
                settings.llm_rate_limit,
            )
            return False

        _request_timestamps.append(now)
        return True


# ── Ollama availability cache ────────────────────────────────────

_ollama_available: bool | None = None
_ollama_last_check: float = 0
_OLLAMA_CHECK_INTERVAL = 60  # Re-check every 60 seconds

# ── Classification result cache ──────────────────────────────────

_classification_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 86400  # 24 hours


# ── JSON extraction utility ──────────────────────────────────────


def extract_json(text: str) -> dict | list | None:
    """Extract JSON from an LLM response, handling markdown code blocks.

    Tries multiple strategies:
    1. Direct JSON parse
    2. Strip markdown ```json ... ``` blocks
    3. Regex search for JSON-like content
    """
    text = text.strip()

    # Remove markdown code blocks if present
    md_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if md_match:
        text = md_match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON-like content (object or array)
    for pattern in [r"\{[\s\S]*\}", r"\[[\s\S]*\]"]:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    return None


# ── Backend: Gemini API ──────────────────────────────────────────


async def _gemini_generate(
    prompt: str,
    system: str,
    *,
    timeout: float = _GEMINI_TIMEOUT,
    temperature: float = 0.1,
    max_tokens: int = 256,
    json_mode: bool = False,
) -> str | None:
    """Send a request to the Gemini REST API and return the response text."""
    if not settings.gemini_api_key:
        return None

    if not await _acquire_rate_limit():
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )

    # Build the request body
    contents = [
        {"role": "user", "parts": [{"text": prompt}]},
    ]

    generation_config: dict = {
        "temperature": temperature,
        "maxOutputTokens": max_tokens,
    }
    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    payload = {
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": generation_config,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract text from Gemini response
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()

            logger.warning("Gemini returned empty response: %s", data)
            return None

    except httpx.TimeoutException:
        logger.warning("Gemini request timed out (%.1fs)", timeout)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("Gemini HTTP %d: %s", e.response.status_code, e.response.text[:200])
        return None
    except Exception as e:
        logger.warning("Gemini unexpected error: %s", e)
        return None


# ── Backend: Ollama (local) ──────────────────────────────────────


async def _ollama_generate(
    prompt: str,
    system: str,
    *,
    timeout: float = _OLLAMA_TIMEOUT,
    temperature: float = 0.1,
    num_predict: int = 50,
    json_mode: bool = False,
) -> str | None:
    """Send a generate request to Ollama and return the response text."""
    if not settings.ollama_url:
        return None

    if not await _acquire_rate_limit():
        return None

    payload: dict = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }
    if json_mode:
        payload["format"] = "json"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    except httpx.TimeoutException:
        logger.warning("Ollama request timed out (%.1fs)", timeout)
        return None
    except httpx.HTTPError as e:
        logger.warning("Ollama HTTP error: %s", e)
        return None
    except Exception as e:
        logger.warning("Ollama unexpected error: %s", e)
        return None


# ── Unified LLM call (Gemini → Ollama fallback) ─────────────────


async def _llm_generate(
    prompt: str,
    system: str,
    *,
    temperature: float = 0.1,
    max_tokens: int = 256,
    json_mode: bool = False,
    timeout: float | None = None,
    batch: bool = False,
) -> str | None:
    """Try Gemini first, fall back to Ollama if Gemini is unavailable.

    This is the single entry point for all LLM calls in the service.
    """
    # ── Try Gemini first ──
    if settings.gemini_api_key:
        gemini_timeout = timeout or (_GEMINI_BATCH_TIMEOUT if batch else _GEMINI_TIMEOUT)
        result = await _gemini_generate(
            prompt=prompt,
            system=system,
            timeout=gemini_timeout,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        )
        if result is not None:
            return result
        logger.debug("Gemini failed or rate-limited, trying Ollama fallback")

    # ── Fallback to Ollama ──
    if settings.ollama_url and await is_ollama_available():
        ollama_timeout = timeout or (_OLLAMA_BATCH_TIMEOUT if batch else _OLLAMA_TIMEOUT)
        result = await _ollama_generate(
            prompt=prompt,
            system=system,
            timeout=ollama_timeout,
            temperature=temperature,
            num_predict=max_tokens,
            json_mode=json_mode,
        )
        if result is not None:
            return result

    return None


# ── Department classification ────────────────────────────────────

_CLASSIFY_SYSTEM = """אתה מסווג מוצרים למחלקות בסופרמרקט ישראלי.

המחלקות האפשריות:
ירקות ופירות, מוצרי חלב, בשר ודגים, מאפים, קפואים, משקאות, חטיפים, מזווה, ניקיון, טיפוח, תינוקות, חיות מחמד

דוגמאות:
פריט: "אקטיביה תות" → מחלקה: "מוצרי חלב"
פריט: "שוקולד פרה" → מחלקה: "חטיפים"
פריט: "סבון כלים פיירי" → מחלקה: "ניקיון"
פריט: "קוסקוס אסם" → מחלקה: "מזווה"
פריט: "פרגיות טריות" → מחלקה: "בשר ודגים"
פריט: "בייגלה עגול" → מחלקה: "חטיפים"
פריט: "XL חיתולים" → מחלקה: "תינוקות"
פריט: "קולה זירו" → מחלקה: "משקאות"

ענה אך ורק בשם המחלקה, ללא הסבר נוסף.
אם אינך יודע, ענה: "אחר"
"""


def _validate_department(result: str) -> str | None:
    """Validate and normalize an LLM department response to a known Hebrew department."""
    if not result:
        return None

    result = result.strip().strip('"').strip("'").strip()

    # Exact match
    if result in DEPARTMENTS_HE:
        return result

    # Partial match (department name contained in response)
    for dept in DEPARTMENTS_HE:
        if dept in result:
            return dept

    # English response → translate to Hebrew
    result_lower = result.lower().strip()
    for dept in DEPARTMENTS_EN:
        if dept.lower() in result_lower:
            return DEPT_EN_TO_HE.get(dept, dept)

    return None


async def classify_department(item_name: str) -> Optional[str]:
    """
    Use LLM to classify a grocery item into a store department.

    Checks in-memory cache first. Always returns the Hebrew department name,
    or None if the LLM is unavailable or fails.
    """
    # Check cache first
    normalized = item_name.strip().lower()
    if normalized in _classification_cache:
        cached_result, timestamp = _classification_cache[normalized]
        if time.time() - timestamp < _CACHE_TTL:
            logger.debug("Cache hit for '%s' → '%s'", item_name, cached_result)
            return cached_result

    user_prompt = f'פריט: "{item_name}" → מחלקה:'

    result = await _llm_generate(
        prompt=user_prompt,
        system=_CLASSIFY_SYSTEM,
        temperature=0.1,
        max_tokens=30,
    )

    if result is None:
        return None

    department = _validate_department(result)

    if department:
        _classification_cache[normalized] = (department, time.time())
        logger.info("LLM classified '%s' → '%s'", item_name, department)
    else:
        logger.warning(
            "LLM returned unknown department '%s' for item '%s'",
            result,
            item_name,
        )

    return department


async def classify_departments_batch(
    item_names: list[str],
) -> dict[str, str | None]:
    """
    Classify multiple items in a single LLM call.

    Returns a mapping of {item_name: hebrew_department_name}.
    Falls back to individual classification if batch fails.
    """
    if not item_names:
        return {}

    # Check cache for all items first
    results: dict[str, str | None] = {}
    uncached: list[str] = []

    for name in item_names:
        normalized = name.strip().lower()
        if normalized in _classification_cache:
            cached_result, timestamp = _classification_cache[normalized]
            if time.time() - timestamp < _CACHE_TTL:
                results[name] = cached_result
                continue
        uncached.append(name)

    if not uncached:
        return results

    # Single item → use regular classify
    if len(uncached) == 1:
        results[uncached[0]] = await classify_department(uncached[0])
        return results

    # Build batch prompt
    items_list = "\n".join(
        f"{i + 1}. {name}" for i, name in enumerate(uncached)
    )

    batch_system = """אתה מסווג מוצרים למחלקות בסופרמרקט ישראלי.

המחלקות האפשריות:
ירקות ופירות, מוצרי חלב, בשר ודגים, מאפים, קפואים, משקאות, חטיפים, מזווה, ניקיון, טיפוח, תינוקות, חיות מחמד

דוגמאות:
"אקטיביה תות" → "מוצרי חלב"
"סבון כלים פיירי" → "ניקיון"
"פרגיות טריות" → "בשר ודגים"
"קולה זירו" → "משקאות"

ענה בפורמט JSON בלבד: {"שם_פריט": "שם_מחלקה", ...}
אם אינך יודע, השתמש ב-"אחר".
"""

    batch_prompt = f"סווג את הפריטים הבאים:\n{items_list}"

    raw = await _llm_generate(
        prompt=batch_prompt,
        system=batch_system,
        temperature=0.1,
        max_tokens=500,
        json_mode=True,
        batch=True,
    )

    if raw:
        parsed = extract_json(raw)
        if isinstance(parsed, dict):
            for name in uncached:
                dept_raw = parsed.get(name)
                if dept_raw:
                    dept = _validate_department(str(dept_raw))
                    results[name] = dept
                    if dept:
                        normalized = name.strip().lower()
                        _classification_cache[normalized] = (dept, time.time())
                else:
                    results[name] = None
            return results

    # Fallback: classify individually
    logger.warning("Batch classification failed, falling back to individual calls")
    for name in uncached:
        results[name] = await classify_department(name)

    return results


# ── Smart item parsing ───────────────────────────────────────────

_PARSE_SYSTEM = """אתה עוזר לנתח רשימות קניות. חלץ מהטקסט את הפריטים כ-JSON.

דוגמה:
קלט: "2 קילו עגבניות שרי, חלב תנובה 1 ליטר, 6 ביצים"
פלט:
[
  {"name": "עגבניות שרי", "quantity": "2", "unit": "קילו", "brand": null},
  {"name": "חלב", "quantity": "1", "unit": "ליטר", "brand": "תנובה"},
  {"name": "ביצים", "quantity": "6", "unit": null, "brand": null}
]

דוגמה:
קלט: "חלב, לחם, גבינה צהובה עמק"
פלט:
[
  {"name": "חלב", "quantity": null, "unit": null, "brand": null},
  {"name": "לחם", "quantity": null, "unit": null, "brand": null},
  {"name": "גבינה צהובה", "quantity": null, "unit": null, "brand": "עמק"}
]

דוגמה:
קלט: "3 יוגורט דנונה, אבוקדו, 500 גרם גבינה לבנה"
פלט:
[
  {"name": "יוגורט", "quantity": "3", "unit": null, "brand": "דנונה"},
  {"name": "אבוקדו", "quantity": null, "unit": null, "brand": null},
  {"name": "גבינה לבנה", "quantity": "500", "unit": "גרם", "brand": null}
]

ענה אך ורק ב-JSON תקין (מערך), ללא הסבר נוסף.
"""


async def parse_items_smart(text: str) -> list[dict] | None:
    """
    Use LLM to parse free-text into structured grocery items.

    Returns a list of dicts with keys: name, quantity, unit, brand.
    Returns None if the LLM is unavailable or fails to parse.
    """
    if not text or not text.strip():
        return None

    raw = await _llm_generate(
        prompt=f"קלט: \"{text}\"\nפלט:",
        system=_PARSE_SYSTEM,
        temperature=0.1,
        max_tokens=500,
        json_mode=True,
    )

    if raw is None:
        return None

    parsed = extract_json(raw)

    if not isinstance(parsed, list):
        logger.warning("LLM parse returned non-list: %s", raw[:200])
        return None

    # Validate and normalize each item
    items: list[dict] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            continue
        items.append(
            {
                "name": name.strip(),
                "quantity": str(entry["quantity"]).strip() if entry.get("quantity") else None,
                "unit": str(entry["unit"]).strip() if entry.get("unit") else None,
                "brand": str(entry["brand"]).strip() if entry.get("brand") else None,
            }
        )

    if not items:
        logger.warning("LLM parse returned no valid items from: %s", text[:200])
        return None

    logger.info("LLM parsed %d items from text", len(items))
    return items


# ── Natural language intent understanding ────────────────────────

_INTENT_SYSTEM = """אתה עוזר לנהל רשימת קניות. נתח את כוונת המשתמש.

פעולות אפשריות: add, remove, done, list, sort, clear, help, unknown

דוגמאות:
"תוסיף חלב ולחם" → {"action": "add", "items": ["חלב", "לחם"]}
"תוסיפי בבקשה ביצים" → {"action": "add", "items": ["ביצים"]}
"תוריד את הביצים" → {"action": "remove", "items": ["ביצים"]}
"תמחק חלב מהרשימה" → {"action": "remove", "items": ["חלב"]}
"קניתי חלב" → {"action": "done", "items": ["חלב"]}
"לקחתי את הלחם" → {"action": "done", "items": ["לחם"]}
"מה ברשימה?" → {"action": "list", "items": []}
"תראה לי את הרשימה" → {"action": "list", "items": []}
"תמיין לפי מחלקות" → {"action": "sort", "items": []}
"תנקה הכל" → {"action": "clear", "items": []}
"עזרה" → {"action": "help", "items": []}
"מה אפשר לעשות?" → {"action": "help", "items": []}
"מה שלומך?" → {"action": "unknown", "items": []}

חשוב מאוד:
- אם המשתמש מזכיר פריטים בכל צורה שהיא (גם בלי פועל ברור), זו כנראה הוספה (add).
- "חלב ולחם" → add. "ביצים, גבינה" → add.
- אם יש ספק, העדף add על unknown.

ענה אך ורק ב-JSON תקין, ללא הסבר נוסף.
"""


async def understand_intent(text: str) -> dict | None:
    """
    Use LLM to understand user intent from natural language.

    Returns a dict with keys: action, items.
    action is one of: add, remove, done, list, sort, clear, help, unknown.
    items is a list of item name strings (may be empty).

    Returns None if the LLM is unavailable or fails.
    """
    if not text or not text.strip():
        return None

    raw = await _llm_generate(
        prompt=f'"{text}"',
        system=_INTENT_SYSTEM,
        temperature=0.1,
        max_tokens=200,
        json_mode=True,
    )

    if raw is None:
        return None

    parsed = extract_json(raw)

    if not isinstance(parsed, dict):
        logger.warning("LLM intent returned non-dict: %s", raw[:200])
        return None

    action = parsed.get("action")
    items = parsed.get("items", [])

    valid_actions = {"add", "remove", "done", "list", "sort", "clear", "help", "unknown"}
    if action not in valid_actions:
        logger.warning("LLM returned unknown action '%s'", action)
        return None

    # Normalize items to list of strings
    if not isinstance(items, list):
        items = []
    items = [str(i).strip() for i in items if i and str(i).strip()]

    logger.info("LLM intent: action=%s, items=%s", action, items)
    return {"action": action, "items": items}


# ── Availability checks ──────────────────────────────────────────


def is_gemini_configured() -> bool:
    """Return True if a Gemini API key is configured."""
    return bool(settings.gemini_api_key)


async def is_ollama_available() -> bool:
    """Check if the Ollama service is reachable. Caches result for 60 seconds."""
    global _ollama_available, _ollama_last_check

    if not settings.ollama_url:
        return False

    now = time.time()
    if (
        _ollama_available is not None
        and (now - _ollama_last_check) < _OLLAMA_CHECK_INTERVAL
    ):
        return _ollama_available

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            _ollama_available = response.status_code == 200
    except Exception:
        _ollama_available = False

    _ollama_last_check = now

    if _ollama_available:
        logger.info("Ollama is available at %s", settings.ollama_url)
    else:
        logger.info(
            "Ollama is not available at %s",
            settings.ollama_url,
        )

    return bool(_ollama_available)


async def is_llm_available() -> bool:
    """Return True if any LLM backend (Gemini or Ollama) is available."""
    if is_gemini_configured():
        return True
    return await is_ollama_available()
