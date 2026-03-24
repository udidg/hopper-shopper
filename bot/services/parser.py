"""Parse free-text messages into grocery item names."""

import re


def parse_items_text(text: str) -> list[str]:
    """
    Parse a text message into individual grocery item names.

    Supports:
    - One item per line
    - Comma-separated items
    - Numbered lists (1. item, 2. item)
    - Bullet lists (- item, • item, * item)
    - Mixed formats

    Returns a deduplicated list of cleaned item names.
    """
    if not text or not text.strip():
        return []

    # Split by newlines first
    lines = text.strip().split("\n")

    items: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Remove common list prefixes: "1.", "1)", "-", "•", "*", "·"
        line = re.sub(r"^\s*(\d+[.)]\s*|[-•*·]\s*)", "", line)

        # Split by commas if the line contains them
        if "," in line:
            parts = line.split(",")
        else:
            parts = [line]

        for part in parts:
            cleaned = part.strip()
            # Skip empty or very short items (likely noise)
            if cleaned and len(cleaned) >= 1:
                items.append(cleaned)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_items: list[str] = []
    for item in items:
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            unique_items.append(item)

    return unique_items


def looks_like_grocery_list(text: str) -> bool:
    """
    Heuristic: does this message look like a grocery list?

    Returns True if the message has multiple lines or comma-separated items
    that could be grocery items.
    """
    if not text or len(text) < 3:
        return False

    # Skip messages that look like commands or URLs
    if text.startswith("/") or text.startswith("http"):
        return False

    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    # Multi-line message with 2+ lines of short text
    if len(lines) >= 2:
        # Check that most lines are short (typical grocery items)
        short_lines = sum(1 for l in lines if len(l) < 50)
        return short_lines >= len(lines) * 0.6

    # Single line with commas (comma-separated list)
    if "," in text:
        parts = [p.strip() for p in text.split(",") if p.strip()]
        return len(parts) >= 2

    return False
