"""Beautified Hebrew message formatting for grocery lists.

Uses plain text (no Markdown) to avoid escaping issues with Hebrew item names
that may contain special characters like quotes, asterisks, etc.
"""

from __future__ import annotations

from datetime import datetime

from bot.services.grouping import DEPARTMENTS_HE, DEPT_ORDER

# Emoji mapping for each department
DEPT_EMOJI: dict[str, str] = {
    "ירקות ופירות": "🥬",
    "מוצרי חלב": "🧀",
    "בשר ודגים": "🥩",
    "מאפים": "🍞",
    "קפואים": "🧊",
    "משקאות": "☕",
    "חטיפים": "🍿",
    "מזווה": "🫙",
    "ניקיון": "🧹",
    "טיפוח": "🧴",
    "תינוקות": "👶",
    "חיות מחמד": "🐾",
}

# Default emoji for uncategorized items
DEFAULT_DEPT = "אחר"
DEFAULT_EMOJI = "📦"


# ── Unified item detail formatter ─────────────────────────────────


def _build_qty_str(item: dict) -> str | None:
    """Build a quantity string like '2 קילו' from an item dict."""
    quantity = item.get("quantity")
    if not quantity:
        return None
    unit = item.get("unit")
    return f"{quantity} {unit}" if unit else str(quantity)


def format_item_detail(item: dict, style: str = "inline") -> str:
    """Format item details in a consistent style.

    Styles:
      - ``"inline"``: compact, for button labels / toasts → ``"חלב x2"``
      - ``"line"``:   single line, for /list and /sort   → ``"חלב (2 ליטר, תנובה)"``
      - ``"card"``:   multi-line detail card with emojis  → full card
    """
    name = item.get("name", "")
    brand = item.get("brand")
    qty_str = _build_qty_str(item)
    desc = item.get("description")
    price = item.get("price")
    category = item.get("category")
    added_by_name = item.get("added_by_name")
    created_at = item.get("created_at")

    # Avoid showing description if it duplicates brand
    if desc and desc == brand:
        desc = None

    if style == "inline":
        # Compact: "חלב x2" or "חלב (תנובה · 2 ליטר)"
        hints: list[str] = []
        if brand:
            hints.append(brand)
        if qty_str:
            hints.append(qty_str)
        if desc:
            hints.append(desc)
        if price is not None:
            hints.append(f"₪{float(price):.2f}")
        if hints:
            return f"{name} ({' · '.join(hints)})"
        return name

    if style == "line":
        # Single line: "חלב (2 ליטר, תנובה) ₪7.90"
        parts: list[str] = []
        if qty_str:
            parts.append(qty_str)
        if brand:
            parts.append(brand)
        if desc:
            parts.append(desc)
        result = name
        if parts:
            result += f" ({', '.join(parts)})"
        if price is not None:
            result += f" ₪{float(price):.2f}"
        return result

    # style == "card"
    lines: list[str] = [f"📦 {name}"]
    if brand:
        lines.append(f"🏷️ {brand}")
    if qty_str:
        lines.append(f"📏 {qty_str}")
    if desc:
        lines.append(f"📝 {desc}")
    if category:
        dept_emoji = DEPT_EMOJI.get(category, DEFAULT_EMOJI)
        lines.append(f"{dept_emoji} {category}")
    if price is not None:
        lines.append(f"💰 ₪{float(price):.2f}")
    if added_by_name:
        lines.append(f"👤 {added_by_name}")
    if created_at:
        if isinstance(created_at, datetime):
            lines.append(f"📅 {created_at.strftime('%d/%m/%Y %H:%M')}")
        elif isinstance(created_at, str):
            lines.append(f"📅 {created_at}")
    return "\n".join(lines)


# ── List formatters ───────────────────────────────────────────────


def format_sorted_list(
    items: list[dict],
    list_name: str = "רשימת קניות",
    show_done: bool = False,
) -> str:
    """
    Format a list of items grouped by department into a beautified Hebrew message.

    Args:
        items: List of dicts with keys: name, category, is_done, price, description
        list_name: Name of the grocery list
        show_done: Whether to include done items

    Returns:
        Formatted plain-text message string with emojis and department grouping.
    """
    if not items:
        return "📝 הרשימה ריקה!"

    # Group items by department
    groups: dict[str, list[dict]] = {}
    for item in items:
        if not show_done and item.get("is_done", False):
            continue
        dept = item.get("category") or DEFAULT_DEPT
        if dept not in groups:
            groups[dept] = []
        groups[dept].append(item)

    if not groups:
        return "✅ כל הפריטים נקנו! הרשימה הושלמה 🎉"

    # Sort departments by predefined order
    sorted_depts = sorted(
        groups.keys(),
        key=lambda d: DEPT_ORDER.get(d, 999),
    )

    # Build the message
    lines: list[str] = [f"🛒 {list_name}", ""]

    total_items = sum(len(g) for g in groups.values())
    done_count = sum(
        1 for item in items if item.get("is_done", False)
    )

    for dept in sorted_depts:
        emoji = DEPT_EMOJI.get(dept, DEFAULT_EMOJI)
        lines.append(f"{emoji} {dept}")

        for item in groups[dept]:
            is_done = item.get("is_done", False)
            prefix = "  ✅" if is_done else "  •"
            detail_line = format_item_detail(item, style="line")
            lines.append(f"{prefix} {detail_line}")

        lines.append("")  # Empty line between departments

    # Footer with stats
    lines.append(f"📊 {total_items} פריטים")
    if done_count > 0:
        lines.append(f"✅ {done_count} נקנו")

    return "\n".join(lines)


def format_plain_list(items: list[dict], list_name: str = "רשימת קניות") -> str:
    """
    Format a simple unsorted list (for /list command).

    Args:
        items: List of dicts with keys: name, is_done, price, description
        list_name: Name of the grocery list

    Returns:
        Simple formatted plain-text message.
    """
    if not items:
        return "📝 הרשימה ריקה!"

    lines: list[str] = [f"📋 {list_name}", ""]

    pending = [i for i in items if not i.get("is_done", False)]
    done = [i for i in items if i.get("is_done", False)]

    if pending:
        for item in pending:
            detail_line = format_item_detail(item, style="line")
            lines.append(f"  ☐ {detail_line}")

    if done:
        lines.append("")
        lines.append("✅ נקנו:")
        for item in done:
            lines.append(f"  ✓ {item['name']}")

    lines.append("")
    lines.append(f"📊 {len(pending)} נותרו | {len(done)} נקנו")

    return "\n".join(lines)


def format_items_added(items) -> str:
    """Format a confirmation message for added items.

    Accepts either:
    - list of strings (item names)
    - list of dicts with 'name' and optional 'detail' keys
    """
    if not items:
        return "לא נוספו פריטים."

    # Normalize to list of dicts
    normalized: list[dict] = []
    for item in items:
        if isinstance(item, str):
            normalized.append({"name": item})
        else:
            normalized.append(item)

    if len(normalized) == 1:
        entry = normalized[0]
        detail = entry.get("detail")
        if detail:
            return f"✅ {entry['name']} נוסף לרשימה! ({detail})"
        return f"✅ {entry['name']} נוסף לרשימה!"

    lines = []
    for entry in normalized:
        detail = entry.get("detail")
        if detail:
            lines.append(f"  • {entry['name']} ({detail})")
        else:
            lines.append(f"  • {entry['name']}")

    items_text = "\n".join(lines)
    return f"✅ {len(normalized)} פריטים נוספו לרשימה:\n{items_text}"


def format_items_removed(item_names: list[str]) -> str:
    """Format a confirmation message for removed items."""
    if not item_names:
        return "לא נמצאו פריטים להסרה."

    if len(item_names) == 1:
        return f"🗑️ {item_names[0]} הוסר מהרשימה."

    items_text = "\n".join(f"  • {name}" for name in item_names)
    return f"🗑️ {len(item_names)} פריטים הוסרו:\n{items_text}"


def format_help() -> str:
    """Format the help message in Hebrew."""
    return """🛒 Hopper Shopper Bot — עזרה

📝 ניהול רשימה:
  /add פריט1, פריט2 — הוספת פריטים לרשימה
  /remove פריט — הסרת פריט מהרשימה
  /done פריט — סימון פריט כנקנה
  /undone פריט — ביטול סימון פריט

📋 תצוגה:
  /list — הצגת הרשימה הנוכחית
  /sort — מיון הרשימה לפי מחלקות

🛍️ קניות:
  /shop — מצב קניות עם כפתורים אינטראקטיביים

🗑️ ניקוי:
  /clear — ניקוי כל הרשימה (עם אישור)
  /cleardone — ניקוי רק פריטים שנקנו

💰 מחירים ופרטים:
  /price פריט מחיר — עדכון מחיר פריט
  /detail — בחירת פריט לעריכת פרטים (מצב מודרך)
  /detail פריט פרטים — שמירת פרטים ישירה

📊 מידע:
  /help — הצגת עזרה זו

💡 טיפים:
  • שלחו רשימה כטקסט חופשי (פריט בכל שורה) והבוט יזהה ויסדר אותה אוטומטית
  • כתבו בשפה חופשית: "תוסיף חלב ולחם", "קניתי ביצים", "מה ברשימה?"
  • הבוט מזהה כמויות ומותגים: "2 קילו עגבניות שרי, חלב תנובה 1 ליטר"
  • במצב קניות (/shop), לחצו ℹ️ ליד פריט כדי לראות פרטים מלאים
  • השתמשו ב-/detail כדי לשמור מותג מועדף — למשל: /detail תפוחי אדמה של דוד משה
  • כשהרשימה ריקה, /list יציע פריטים שאתם בדרך כלל קונים"""
