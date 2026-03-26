"""Auto-grouping logic – assigns a store section category to items.

Reused and adapted from the original backend/app/services/grouping.py.
All classification returns Hebrew department names.
"""

import re

# ── English category map: keyword → category ─────────────────────
CATEGORY_MAP: dict[str, str] = {
    # Produce
    "apple": "Produce", "banana": "Produce", "tomato": "Produce",
    "lettuce": "Produce", "onion": "Produce", "potato": "Produce",
    "carrot": "Produce", "pepper": "Produce", "cucumber": "Produce",
    "avocado": "Produce", "lemon": "Produce", "lime": "Produce",
    "orange": "Produce", "grape": "Produce", "strawberry": "Produce",
    "blueberry": "Produce", "garlic": "Produce", "ginger": "Produce",
    "herb": "Produce", "basil": "Produce", "cilantro": "Produce",
    "parsley": "Produce", "mushroom": "Produce",
    # Dairy
    "milk": "Dairy", "cheese": "Dairy", "yogurt": "Dairy",
    "butter": "Dairy", "cream": "Dairy", "egg": "Dairy", "cottage": "Dairy",
    # Meat & Seafood
    "chicken": "Meat & Seafood", "beef": "Meat & Seafood",
    "pork": "Meat & Seafood", "fish": "Meat & Seafood",
    "salmon": "Meat & Seafood", "shrimp": "Meat & Seafood",
    "turkey": "Meat & Seafood", "sausage": "Meat & Seafood",
    "bacon": "Meat & Seafood",
    # Bakery
    "bread": "Bakery", "bagel": "Bakery", "roll": "Bakery",
    "muffin": "Bakery", "croissant": "Bakery", "pita": "Bakery",
    "tortilla": "Bakery",
    # Frozen
    "frozen": "Frozen", "ice cream": "Frozen", "pizza": "Frozen",
    # Beverages
    "water": "Beverages", "juice": "Beverages", "soda": "Beverages",
    "coffee": "Beverages", "tea": "Beverages", "beer": "Beverages",
    "wine": "Beverages",
    # Snacks
    "chip": "Snacks", "cracker": "Snacks", "cookie": "Snacks",
    "pretzel": "Snacks", "popcorn": "Snacks", "nut": "Snacks",
    # Pantry / Dry Goods
    "rice": "Pantry", "pasta": "Pantry", "cereal": "Pantry",
    "flour": "Pantry", "sugar": "Pantry", "oil": "Pantry",
    "vinegar": "Pantry", "sauce": "Pantry", "can": "Pantry",
    "bean": "Pantry", "soup": "Pantry", "spice": "Pantry", "salt": "Pantry",
    # Cleaning
    "soap": "Cleaning", "detergent": "Cleaning", "bleach": "Cleaning",
    "sponge": "Cleaning", "paper towel": "Cleaning", "trash bag": "Cleaning",
    "wipe": "Cleaning", "cleaner": "Cleaning",
    # Personal Care
    "shampoo": "Personal Care", "toothpaste": "Personal Care",
    "deodorant": "Personal Care", "lotion": "Personal Care",
    "razor": "Personal Care", "tissue": "Personal Care",
    "toilet paper": "Personal Care",
    # Baby
    "diaper": "Baby", "formula": "Baby", "baby food": "Baby",
    "baby wipe": "Baby",
    # Pet
    "dog food": "Pet", "cat food": "Pet", "pet": "Pet",
}

# ── Hebrew category map: keyword → category (Hebrew names) ───────
HEBREW_CATEGORY_MAP: dict[str, str] = {
    # ירקות ופירות (Produce) — singular + plural forms
    "תפוח": "ירקות ופירות", "תפוחים": "ירקות ופירות",
    "בננה": "ירקות ופירות", "בננות": "ירקות ופירות",
    "עגבנייה": "ירקות ופירות", "עגבניה": "ירקות ופירות",
    "עגבניות": "ירקות ופירות",
    "חסה": "ירקות ופירות", "חסות": "ירקות ופירות",
    "בצל": "ירקות ופירות", "בצלים": "ירקות ופירות",
    "תפוח אדמה": "ירקות ופירות", "תפוחי אדמה": "ירקות ופירות",
    'תפו"א': "ירקות ופירות",
    "גזר": "ירקות ופירות", "גזרים": "ירקות ופירות",
    "פלפל": "ירקות ופירות", "פלפלים": "ירקות ופירות",
    "מלפפון": "ירקות ופירות", "מלפפונים": "ירקות ופירות",
    "אבוקדו": "ירקות ופירות",
    "לימון": "ירקות ופירות", "לימונים": "ירקות ופירות",
    "תפוז": "ירקות ופירות", "תפוזים": "ירקות ופירות",
    "ענבים": "ירקות ופירות", "תות": "ירקות ופירות", "תותים": "ירקות ופירות",
    "אוכמניות": "ירקות ופירות", "שום": "ירקות ופירות",
    "ג'ינג'ר": "ירקות ופירות", "זנגביל": "ירקות ופירות",
    "בזיליקום": "ירקות ופירות", "כוסברה": "ירקות ופירות",
    "פטרוזיליה": "ירקות ופירות", "פטריות": "ירקות ופירות",
    "כרוב": "ירקות ופירות", "ברוקולי": "ירקות ופירות",
    "כרובית": "ירקות ופירות", "סלרי": "ירקות ופירות",
    "קישוא": "ירקות ופירות", "קישואים": "ירקות ופירות",
    "חציל": "ירקות ופירות", "חצילים": "ירקות ופירות",
    "צנונית": "ירקות ופירות", "צנוניות": "ירקות ופירות",
    "אפרסק": "ירקות ופירות", "אפרסקים": "ירקות ופירות",
    "שזיף": "ירקות ופירות", "שזיפים": "ירקות ופירות",
    "אגס": "ירקות ופירות", "אגסים": "ירקות ופירות",
    "מנגו": "ירקות ופירות", "אננס": "ירקות ופירות",
    "אבטיח": "ירקות ופירות", "אבטיחים": "ירקות ופירות",
    "מלון": "ירקות ופירות", "מלונים": "ירקות ופירות",
    "רימון": "ירקות ופירות", "רימונים": "ירקות ופירות",
    "קלמנטינה": "ירקות ופירות", "קלמנטינות": "ירקות ופירות",
    "פומלה": "ירקות ופירות", "פומלות": "ירקות ופירות",
    "ירק": "ירקות ופירות", "ירקות": "ירקות ופירות",
    "פרי": "ירקות ופירות", "פירות": "ירקות ופירות",
    # מוצרי חלב (Dairy)
    "חלב": "מוצרי חלב", "גבינה": "מוצרי חלב", "גבינות": "מוצרי חלב",
    "יוגורט": "מוצרי חלב", "חמאה": "מוצרי חלב",
    "שמנת": "מוצרי חלב", "ביצה": "מוצרי חלב",
    "ביצים": "מוצרי חלב", "קוטג'": "מוצרי חלב",
    "קוטג": "מוצרי חלב", "לבן": "מוצרי חלב",
    "שוקו": "מוצרי חלב", "גבינה צהובה": "מוצרי חלב",
    "גבינה לבנה": "מוצרי חלב", "מוצרלה": "מוצרי חלב",
    "שמנת חמוצה": "מוצרי חלב",
    # בשר ודגים (Meat & Seafood)
    "עוף": "בשר ודגים", "בשר": "בשר ודגים",
    "דג": "בשר ודגים", "דגים": "בשר ודגים",
    "סלמון": "בשר ודגים",
    "הודו": "בשר ודגים", "נקניק": "בשר ודגים", "נקניקים": "בשר ודגים",
    "נקניקייה": "בשר ודגים", "נקניקיות": "בשר ודגים",
    "שניצל": "בשר ודגים", "שניצלים": "בשר ודגים",
    "כבד": "בשר ודגים", "טחון": "בשר ודגים",
    "סטייק": "בשר ודגים", "סטייקים": "בשר ודגים",
    "פרגית": "בשר ודגים", "פרגיות": "בשר ודגים",
    "כנפיים": "בשר ודגים", "חזה עוף": "בשר ודגים",
    "שוק עוף": "בשר ודגים", "שוקיים": "בשר ודגים",
    "טונה": "בשר ודגים",
    "אמנון": "בשר ודגים", "דניס": "בשר ודגים",
    "המבורגר": "בשר ודגים", "קבב": "בשר ודגים",
    # מאפים (Bakery)
    "לחם": "מאפים", "פיתה": "מאפים", "פיתות": "מאפים",
    "בגט": "מאפים",
    "חלה": "מאפים", "חלות": "מאפים",
    "לחמנייה": "מאפים", "לחמניה": "מאפים", "לחמניות": "מאפים",
    "קרואסון": "מאפים", "קרואסונים": "מאפים",
    "טורטייה": "מאפים", "טורטיות": "מאפים",
    "לפה": "מאפים", "לפות": "מאפים",
    "עוגה": "מאפים", "עוגות": "מאפים",
    "בורקס": "מאפים", "בורקסים": "מאפים",
    # קפואים (Frozen)
    "קפוא": "קפואים", "גלידה": "קפואים", "גלידות": "קפואים",
    "פיצה": "קפואים", "פיצות": "קפואים",
    "שניצל קפוא": "קפואים", "ירקות קפואים": "קפואים",
    # משקאות (Beverages)
    "מים": "משקאות", "מיץ": "משקאות", "מיצים": "משקאות",
    "סודה": "משקאות",
    "קפה": "משקאות", "תה": "משקאות", "בירה": "משקאות", "בירות": "משקאות",
    "יין": "משקאות", "יינות": "משקאות",
    "קולה": "משקאות", "לימונדה": "משקאות",
    # חטיפים (Snacks)
    "חטיף": "חטיפים", "חטיפים": "חטיפים",
    "ביסלי": "חטיפים", "במבה": "חטיפים",
    "קרקר": "חטיפים", "קרקרים": "חטיפים",
    "עוגייה": "חטיפים", "עוגיות": "חטיפים",
    "פופקורן": "חטיפים", "אגוזים": "חטיפים", "שוקולד": "חטיפים",
    "סוכריות": "חטיפים", "צ'יפס": "חטיפים", "פריצל": "חטיפים",
    # מזווה (Pantry)
    "אורז": "מזווה", "פסטה": "מזווה", "קמח": "מזווה",
    "סוכר": "מזווה", "שמן": "מזווה", "חומץ": "מזווה",
    "רוטב": "מזווה", "רטבים": "מזווה",
    "שימורים": "מזווה", "שעועית": "מזווה",
    "עדשים": "מזווה", "חומוס": "מזווה", "טחינה": "מזווה",
    "מרק": "מזווה", "מרקים": "מזווה",
    "תבלין": "מזווה", "תבלינים": "מזווה",
    "מלח": "מזווה",
    "פלפל שחור": "מזווה", "פפריקה": "מזווה", "כורכום": "מזווה",
    "קורנפלקס": "מזווה", "דגני בוקר": "מזווה",
    "רסק עגבניות": "מזווה", "קטשופ": "מזווה",
    "חרדל": "מזווה", "מיונז": "מזווה", "סויה": "מזווה",
    "אטריות": "מזווה", "נודלס": "מזווה", "קוסקוס": "מזווה",
    # ניקיון (Cleaning)
    "סבון": "ניקיון", "אקונומיקה": "ניקיון",
    "ספוג": "ניקיון", "ספוגים": "ניקיון",
    "נייר מגבת": "ניקיון", "שקית אשפה": "ניקיון",
    "שקיות אשפה": "ניקיון", "מגבון": "ניקיון",
    "מגבונים": "ניקיון", "נוזל כלים": "ניקיון",
    "נוזל רצפה": "ניקיון", "אבקת כביסה": "ניקיון",
    "מרכך כביסה": "ניקיון", "מנקה": "ניקיון",
    "אל כתמים": "ניקיון", "כפפות": "ניקיון",
    # טיפוח (Personal Care)
    "שמפו": "טיפוח", "משחת שיניים": "טיפוח",
    "דאודורנט": "טיפוח", "קרם": "טיפוח", "קרמים": "טיפוח",
    "סכין גילוח": "טיפוח", "נייר טואלט": "טיפוח",
    "טישו": "טיפוח", "טישיו": "טיפוח",
    "מברשת שיניים": "טיפוח",
    "מי פה": "טיפוח", "קרם גוף": "טיפוח",
    "מגבונים לחים": "טיפוח",
    # תינוקות (Baby)
    "חיתול": "תינוקות", "חיתולים": "תינוקות",
    "מזון תינוקות": "תינוקות", "מגבוני תינוקות": "תינוקות",
    'תמ"ל': "תינוקות", "תחליף חלב": "תינוקות",
    # חיות מחמד (Pet)
    "מזון כלבים": "חיות מחמד", "מזון חתולים": "חיות מחמד",
    "אוכל לכלב": "חיות מחמד", "אוכל לחתול": "חיות מחמד",
}

# ── All known departments ─────────────────────────────────────────
DEPARTMENTS_EN = [
    "Produce", "Dairy", "Meat & Seafood", "Bakery", "Frozen",
    "Beverages", "Snacks", "Pantry", "Cleaning", "Personal Care",
    "Baby", "Pet",
]

DEPARTMENTS_HE = [
    "ירקות ופירות", "מוצרי חלב", "בשר ודגים", "מאפים", "קפואים",
    "משקאות", "חטיפים", "מזווה", "ניקיון", "טיפוח",
    "תינוקות", "חיות מחמד",
]

# Bidirectional mapping
DEPT_EN_TO_HE: dict[str, str] = dict(zip(DEPARTMENTS_EN, DEPARTMENTS_HE))
DEPT_HE_TO_EN: dict[str, str] = dict(zip(DEPARTMENTS_HE, DEPARTMENTS_EN))

# Department display order (index = sort priority)
DEPT_ORDER: dict[str, int] = {dept: i for i, dept in enumerate(DEPARTMENTS_HE)}

# Regex for detecting Hebrew characters
_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


def is_hebrew(text: str) -> bool:
    """Return True if the text contains Hebrew characters."""
    return bool(_HEBREW_RE.search(text))


def guess_category(item_name: str) -> str | None:
    """
    Guess the store section category for an item name (sync, keyword-only).

    Always returns the Hebrew category name regardless of input language.
    Checks multi-word keys first, then single-word.
    Returns None if no match is found.
    """
    name_lower = item_name.lower().strip()

    if is_hebrew(name_lower):
        for keyword, category in sorted(
            HEBREW_CATEGORY_MAP.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if keyword in name_lower:
                return category
    else:
        for keyword, category in sorted(
            CATEGORY_MAP.items(), key=lambda x: len(x[0]), reverse=True
        ):
            if keyword in name_lower:
                return DEPT_EN_TO_HE.get(category, category)

    return None


async def guess_category_smart(item_name: str) -> str | None:
    """
    Guess the store section category with LLM fallback (async).

    Always returns the Hebrew category name.

    Pipeline:
    1. Try keyword-based matching (fast, no network)
    2. If no match, try LLM classification (Gemini → Ollama)
    3. Return None if both fail
    """
    result = guess_category(item_name)
    if result is not None:
        return result

    # Try LLM (Gemini first, then Ollama fallback — handled inside llm module)
    try:
        from bot.services.llm import classify_department, is_llm_available

        if await is_llm_available():
            llm_result = await classify_department(item_name)
            if llm_result is not None:
                if not is_hebrew(llm_result):
                    llm_result = DEPT_EN_TO_HE.get(llm_result, llm_result)
                return llm_result
    except Exception:
        pass

    return None


async def guess_categories_batch(item_names: list[str]) -> dict[str, str | None]:
    """
    Classify multiple items, using keywords first and LLM batch for the rest.

    Returns a mapping of {item_name: hebrew_department_name}.
    """
    results: dict[str, str | None] = {}
    needs_llm: list[str] = []

    # First pass: keyword matching
    for name in item_names:
        category = guess_category(name)
        if category is not None:
            results[name] = category
        else:
            needs_llm.append(name)

    # Second pass: LLM batch classification for unmatched items
    if needs_llm:
        try:
            from bot.services.llm import (
                classify_departments_batch,
                is_llm_available,
            )

            if await is_llm_available():
                llm_results = await classify_departments_batch(needs_llm)
                for name, dept in llm_results.items():
                    if dept and not is_hebrew(dept):
                        dept = DEPT_EN_TO_HE.get(dept, dept)
                    results[name] = dept
            else:
                for name in needs_llm:
                    results[name] = None
        except Exception:
            for name in needs_llm:
                results[name] = None

    return results
