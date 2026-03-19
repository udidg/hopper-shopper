"""LLM service – uses Ollama for intelligent department classification."""

import logging
from typing import Optional

import httpx

from app.config import settings
from app.services.grouping import (
    DEPARTMENTS_EN,
    DEPARTMENTS_HE,
    DEPT_EN_TO_HE,
    is_hebrew,
)

logger = logging.getLogger(__name__)

# Timeout for Ollama API calls (seconds)
_OLLAMA_TIMEOUT = 10.0

# System prompt for department classification
_SYSTEM_PROMPT = """You are a grocery store department classifier.
Given a grocery item name, classify it into exactly one of these store departments.

Hebrew departments: {departments_he}

Rules:
- ALWAYS respond with the Hebrew department name, regardless of the input language.
- Respond with ONLY the department name, nothing else.
- If you cannot classify the item, respond with "אחר".
"""


async def classify_department(item_name: str) -> Optional[str]:
    """
    Use Ollama to classify a grocery item into a store department.

    Always returns the Hebrew department name,
    or None if the LLM is unavailable or fails.
    """
    if not settings.ollama_url:
        return None

    departments_he = ", ".join(DEPARTMENTS_HE)

    system_prompt = _SYSTEM_PROMPT.format(
        departments_he=departments_he,
    )

    user_prompt = f'Item: "{item_name}"'

    try:
        async with httpx.AsyncClient(timeout=_OLLAMA_TIMEOUT) as client:
            response = await client.post(
                f"{settings.ollama_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": user_prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 50,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            result = data.get("response", "").strip()

            # Validate the result is a known Hebrew department
            if result in DEPARTMENTS_HE:
                return result

            # Try partial match (LLM might add extra text)
            for dept in DEPARTMENTS_HE:
                if dept in result:
                    return dept

            # If LLM returned English, translate to Hebrew
            result_lower = result.lower().strip()
            for dept in DEPARTMENTS_EN:
                if dept.lower() in result_lower:
                    return DEPT_EN_TO_HE.get(dept, dept)

            logger.warning(
                "LLM returned unknown department '%s' for item '%s'",
                result,
                item_name,
            )
            return None

    except httpx.TimeoutException:
        logger.warning("Ollama request timed out for item '%s'", item_name)
        return None
    except httpx.HTTPError as e:
        logger.warning("Ollama HTTP error for item '%s': %s", item_name, e)
        return None
    except Exception as e:
        logger.warning("Ollama unexpected error for item '%s': %s", item_name, e)
        return None


async def is_ollama_available() -> bool:
    """Check if the Ollama service is reachable."""
    if not settings.ollama_url:
        return False

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.ollama_url}/api/tags")
            return response.status_code == 200
    except Exception:
        return False
