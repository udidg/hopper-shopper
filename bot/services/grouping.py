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
    # ירקות ופירות (Produce)
    "תפוח": "ירקות ופירות", "בננה": "ירקות ופירות",
    "עגבנייה": "ירקות ופירות", "עגבניה": "ירקות ופירות",
    "עגבניות": "ירקות ופירות",
    "חסה": "ירקות ופירות", "בצל": "ירקות ופירות",
    "תפוח אדמה": "ירקות ופירות", 'תפו"א': "ירקות ופירות",
    "גזר": "ירקות ופירות", "פלפל": "ירקות ופירות",
    "מלפפון": "ירקות ופירות", "אבוקדו": "ירקות ופירות",
    "לימון": "ירקות ופירות", "תפוז": "ירקות ופירות",
    "ענבים": "ירקות ופירות", "תות": "ירקות ופירות",
    "אוכמניות": "ירקות ופירות", "שום": "ירקות ופירות",
    "ג'ינג'ר": "ירקות ופירות", "זנגביל": "ירקות ופירות",
    "בזיליקום": "ירקות ופירות", "כוסברה": "ירקות ופירות",
    "פטרוזיליה": "ירקות ופירות", "פטריות": "ירקות ופירות",
    "כרוב": "ירקות ופירות", "ברוקולי": "ירקות ופירות",
    "כרובית": "ירקות ופירות", "סלרי": "ירקות ופירות",
    "קישוא": "ירקות ופירות", "חציל": "ירקות ופירות",
    "צנונית": "ירקות ופירות", "אפרסק": "ירקות ופירות",
    "שזיף": "ירקות ופירות", "אגס": "ירקות ופירות",
    "מנגו": "ירקות ופירות", "אננס": "ירקות ופירות",
    "אבטיח": "ירקות ופירות", "מלון": "ירקות ופירות",
    "רימון": "ירקות ופירות", "קלמנטינה": "ירקות ופירות",
    "פומלה": "ירקות ופירות", "ירק": "ירקות ופירות",
    "פרי": "ירקות ופירות",
    # מוצרי חלב (Dairy)
    "חלב": "מוצרי חלב", "גבינה": "מוצרי חלב",
    "יוגורט": "מוצרי חלב", "חמאה": "מוצרי חלב",
    "שמנת": "מוצרי חלב", "ביצה": "מוצרי חלב",
    "ביצים": "מוצרי חלב", "קוטג'": "מוצרי חלב",
    "קוטג": "מוצרי חלב", "לבן": "מוצרי חלב",
    "שוקו": "מוצרי חלב", "גבינה צהובה": "מוצרי חלב",
    "גבינה לבנה": "מוצרי חלב", "מוצרלה": "מוצרי חלב",
    "שמנת חמוצה": "מוצרי חלב",
    # בשר ודגים (Meat & Seafood)
    "עוף": "בשר ודגים", "בשר": "בשר ודגים",
    "דג": "בשר ודגים", "סלמון": "בשר ודגים",
    "הודו": "בשר ודגים", "נקניק": "בשר ודגים",
    "נקניקייה": "בשר ודגים", "שניצל": "בשר ודגים",
    "כבד": "בשר ודגים", "טחון": "בשר ודגים",
    "סטייק": "בשר ודגים", "פרגית": "בשר ודגים",
    "כנפיים": "בשר ודגים", "חזה עוף": "בשר ודגים",
    "שוק עוף": "בשר ודגים", "טונה": "בשר ודגים",
    "אמנון": "בשר ודגים", "דניס": "בשר ודגים",
    # מאפים (Bakery)
    "לחם": "מאפים", "פיתה": "מאפים", "בגט": "מאפים",
    "חלה": "מאפים", "לחמנייה": "מאפים", "לחמניה": "מאפים",
    "קרואסון": "מאפים", "טורטייה": "מאפים", "לפה": "מאפים",
    "עוגה": "מאפים", "בורקס": "מאפים",
    # קפואים (Frozen)
    "קפוא": "קפואים", "גלידה": "קפואים", "פיצה": "קפואים",
    "שניצל קפוא": "קפואים", "ירקות קפואים": "קפואים",
    # משקאות (Beverages)
    "מים": "משקאות", "מיץ": "משקאות", "סודה": "משקאות",
    "קפה": "משקאות", "תה": "משקאות", "בירה": "משקאות",
    "יין": "משקאות", "קולה": "משקאות", "לימונדה": "משקאות",
    # חטיפים (Snacks)
    "חטיף": "חטיפים", "ביסלי": "חטיפים", "במבה": "חטיפים",
    "קרקר": "חטיפים", "עוגייה": "חטיפים", "עוגיות": "חטיפים",
    "פופקורן": "חטיפים", "אגוזים": "חטיפים", "שוקולד": "חטיפים",
    "סוכריות": "חטיפים", "צ'יפס": "חטיפים", "פריצל": "חטיפים",
    # מזווה (Pantry)
    "אורז": "מזווה", "פסטה": "מזווה", "קמח": "מזווה",
    "סוכר": "מזווה", "שמן": "מזווה", "חומץ": "מזווה",
    "רוטב": "מזווה", "שימורים": "מזווה", "שעועית": "מזווה",
    "עדשים": "מזווה", "חומוס": "מזווה", "טחינה": "מזווה",
    "מרק": "מזווה", "תבלין": "מזווה", "מלח": "מזווה",
    "פלפל שחור": "מזווה", "פפריקה": "מזווה", "כורכום": "מזווה",
    "קורנפלקס": "מזווה", "דגני בוקר": "מזווה",
    "רסק עגבניות": "מזווה", "קטשופ": "מזווה",
    "חרדל": "מזווה", "מיונז": "מזווה", "סויה": "מזווה",
    # ניקיון (Cleaning)
    "סבון": "ניקיון", "אקונומיקה": "ניקיון", "ספוג": "ניקיון",
    "נייר מגבת": "ניקיון", "שקית אשפה": "ניקיון",
    "שקיות אשפה": "ניקיון", "מגבון": "ניקיון",
    "מגבונים": "ניקיון", "נוזל כלים": "ניקיון",
    "נוזל רצפה": "ניקיון", "אבקת כביסה": "ניקיון",
    "מרכך כביסה": "ניקיון", "מנקה": "ניקיון",
    # טיפוח (Personal Care)
    "שמפו": "טיפוח", "משחת שיניים": "טיפוח",
    "דאודורנט": "טיפוח", "קרם": "טיפוח",
    "סכין גילוח": "טיפוח", "נייר טואלט": "טיפוח",
    "טישו": "טיפוח", "מברשת שיניים": "טיפוח",
    "מי פה": "טיפוח", "קרם גוף": "טיפוח",
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
    2. If no match, try LLM classification via Ollama (slower, smarter)
    3. Return None if both fail
    """
    result = guess_category(item_name)
    if result is not None:
        return result

    try:
        from bot.services.llm import classify_department
        llm_result = await classify_department(item_name)
        if llm_result is not None:
            if not is_hebrew(llm_result):
                llm_result = DEPT_EN_TO_HE.get(llm_result, llm_result)
            return llm_result
    except Exception:
        pass

    return None
