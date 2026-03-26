"""Beautified Hebrew message formatting for grocery lists.

Uses plain text (no Markdown) to avoid escaping issues with Hebrew item names
that may contain special characters like quotes, asterisks, etc.
"""

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
            name = item["name"]
            is_done = item.get("is_done", False)

            # Build item line
            if is_done:
                item_text = f"  ✅ {name}"
            else:
                item_text = f"  • {name}"

            # Add price if available
            price = item.get("price")
            if price is not None:
                item_text += f" (₪{price:.2f})"

            # Add description if available
            desc = item.get("description")
            if desc:
                item_text += f" — {desc}"

            lines.append(item_text)

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
            line = f"  ☐ {item['name']}"
            price = item.get("price")
            if price is not None:
                line += f" (₪{price:.2f})"
            desc = item.get("description")
            if desc:
                line += f" — {desc}"
            lines.append(line)

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
  /clear — ניקוי כל הרשימה
  /done פריט — סימון פריט כנקנה
  /undone פריט — ביטול סימון פריט

📋 תצוגה:
  /list — הצגת הרשימה הנוכחית
  /sort — מיון הרשימה לפי מחלקות

🛍️ קניות:
  /shop — מצב קניות עם כפתורים אינטראקטיביים

💰 מחירים ופרטים:
  /price פריט מחיר — עדכון מחיר פריט
  /detail פריט פרטים — שמירת מותג/פרטים לפריט

📊 מידע:
  /help — הצגת עזרה זו

💡 טיפים:
  • שלחו רשימה כטקסט חופשי (פריט בכל שורה) והבוט יזהה אותה אוטומטית
  • השתמשו ב-/detail כדי לשמור מותג מועדף — למשל: /detail תפוחי אדמה של דוד משה"""
