"""Auto-grouping logic – assigns a store section category to items."""

# Predefined category map: keyword → category
# This is the fallback when no ItemDictionary match is found.
CATEGORY_MAP: dict[str, str] = {
    # Produce
    "apple": "Produce",
    "banana": "Produce",
    "tomato": "Produce",
    "lettuce": "Produce",
    "onion": "Produce",
    "potato": "Produce",
    "carrot": "Produce",
    "pepper": "Produce",
    "cucumber": "Produce",
    "avocado": "Produce",
    "lemon": "Produce",
    "lime": "Produce",
    "orange": "Produce",
    "grape": "Produce",
    "strawberry": "Produce",
    "blueberry": "Produce",
    "garlic": "Produce",
    "ginger": "Produce",
    "herb": "Produce",
    "basil": "Produce",
    "cilantro": "Produce",
    "parsley": "Produce",
    "mushroom": "Produce",
    # Dairy
    "milk": "Dairy",
    "cheese": "Dairy",
    "yogurt": "Dairy",
    "butter": "Dairy",
    "cream": "Dairy",
    "egg": "Dairy",
    "cottage": "Dairy",
    # Meat & Seafood
    "chicken": "Meat & Seafood",
    "beef": "Meat & Seafood",
    "pork": "Meat & Seafood",
    "fish": "Meat & Seafood",
    "salmon": "Meat & Seafood",
    "shrimp": "Meat & Seafood",
    "turkey": "Meat & Seafood",
    "sausage": "Meat & Seafood",
    "bacon": "Meat & Seafood",
    # Bakery
    "bread": "Bakery",
    "bagel": "Bakery",
    "roll": "Bakery",
    "muffin": "Bakery",
    "croissant": "Bakery",
    "pita": "Bakery",
    "tortilla": "Bakery",
    # Frozen
    "frozen": "Frozen",
    "ice cream": "Frozen",
    "pizza": "Frozen",
    # Beverages
    "water": "Beverages",
    "juice": "Beverages",
    "soda": "Beverages",
    "coffee": "Beverages",
    "tea": "Beverages",
    "beer": "Beverages",
    "wine": "Beverages",
    # Snacks
    "chip": "Snacks",
    "cracker": "Snacks",
    "cookie": "Snacks",
    "pretzel": "Snacks",
    "popcorn": "Snacks",
    "nut": "Snacks",
    # Pantry / Dry Goods
    "rice": "Pantry",
    "pasta": "Pantry",
    "cereal": "Pantry",
    "flour": "Pantry",
    "sugar": "Pantry",
    "oil": "Pantry",
    "vinegar": "Pantry",
    "sauce": "Pantry",
    "can": "Pantry",
    "bean": "Pantry",
    "soup": "Pantry",
    "spice": "Pantry",
    "salt": "Pantry",
    # Cleaning
    "soap": "Cleaning",
    "detergent": "Cleaning",
    "bleach": "Cleaning",
    "sponge": "Cleaning",
    "paper towel": "Cleaning",
    "trash bag": "Cleaning",
    "wipe": "Cleaning",
    "cleaner": "Cleaning",
    # Personal Care
    "shampoo": "Personal Care",
    "toothpaste": "Personal Care",
    "deodorant": "Personal Care",
    "lotion": "Personal Care",
    "razor": "Personal Care",
    "tissue": "Personal Care",
    "toilet paper": "Personal Care",
    # Baby
    "diaper": "Baby",
    "formula": "Baby",
    "baby food": "Baby",
    "baby wipe": "Baby",
    # Pet
    "dog food": "Pet",
    "cat food": "Pet",
    "pet": "Pet",
}


def guess_category(item_name: str) -> str | None:
    """
    Guess the store section category for an item name.

    Checks multi-word keys first (e.g., "paper towel"), then single-word.
    Returns None if no match is found.
    """
    name_lower = item_name.lower()

    # Check multi-word keys first (longer keys = more specific)
    for keyword, category in sorted(
        CATEGORY_MAP.items(), key=lambda x: len(x[0]), reverse=True
    ):
        if keyword in name_lower:
            return category

    return None
