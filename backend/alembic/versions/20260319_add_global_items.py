"""Add global_items table with seed data.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "a4b5ccd70ffc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the global_items table
    global_items = op.create_table(
        "global_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("name_he", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("category_he", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_global_items_name"), "global_items", ["name"])
    op.create_index(op.f("ix_global_items_name_he"), "global_items", ["name_he"])

    # Seed data – common grocery items in English and Hebrew
    op.bulk_insert(
        global_items,
        [
            # ── Produce / ירקות ופירות ──
            {"name": "Apple", "name_he": "תפוח", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Banana", "name_he": "בננה", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Tomato", "name_he": "עגבנייה", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Cucumber", "name_he": "מלפפון", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Onion", "name_he": "בצל", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Potato", "name_he": "תפוח אדמה", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Carrot", "name_he": "גזר", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Pepper", "name_he": "פלפל", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Lettuce", "name_he": "חסה", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Avocado", "name_he": "אבוקדו", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Lemon", "name_he": "לימון", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Orange", "name_he": "תפוז", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Garlic", "name_he": "שום", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Mushroom", "name_he": "פטריות", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Broccoli", "name_he": "ברוקולי", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Cauliflower", "name_he": "כרובית", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Zucchini", "name_he": "קישוא", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Eggplant", "name_he": "חציל", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Grapes", "name_he": "ענבים", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Strawberry", "name_he": "תות", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Watermelon", "name_he": "אבטיח", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Melon", "name_he": "מלון", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Mango", "name_he": "מנגו", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Pineapple", "name_he": "אננס", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Peach", "name_he": "אפרסק", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Pear", "name_he": "אגס", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Pomegranate", "name_he": "רימון", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Clementine", "name_he": "קלמנטינה", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Ginger", "name_he": "ג'ינג'ר", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Parsley", "name_he": "פטרוזיליה", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Cilantro", "name_he": "כוסברה", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Basil", "name_he": "בזיליקום", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Cabbage", "name_he": "כרוב", "category": "Produce", "category_he": "ירקות ופירות"},
            {"name": "Celery", "name_he": "סלרי", "category": "Produce", "category_he": "ירקות ופירות"},
            # ── Dairy / מוצרי חלב ──
            {"name": "Milk", "name_he": "חלב", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Cheese", "name_he": "גבינה", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Yogurt", "name_he": "יוגורט", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Butter", "name_he": "חמאה", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Cream", "name_he": "שמנת", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Eggs", "name_he": "ביצים", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Cottage Cheese", "name_he": "קוטג'", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Sour Cream", "name_he": "שמנת חמוצה", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Yellow Cheese", "name_he": "גבינה צהובה", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "White Cheese", "name_he": "גבינה לבנה", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Mozzarella", "name_he": "מוצרלה", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Chocolate Milk", "name_he": "שוקו", "category": "Dairy", "category_he": "מוצרי חלב"},
            {"name": "Leben", "name_he": "לבן", "category": "Dairy", "category_he": "מוצרי חלב"},
            # ── Meat & Seafood / בשר ודגים ──
            {"name": "Chicken Breast", "name_he": "חזה עוף", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Chicken Thigh", "name_he": "שוק עוף", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Chicken Wings", "name_he": "כנפיים", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Ground Beef", "name_he": "בשר טחון", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Steak", "name_he": "סטייק", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Salmon", "name_he": "סלמון", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Tilapia", "name_he": "אמנון", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Tuna", "name_he": "טונה", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Turkey", "name_he": "הודו", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Schnitzel", "name_he": "שניצל", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Sausage", "name_he": "נקניקייה", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            {"name": "Hot Dog", "name_he": "נקניק", "category": "Meat & Seafood", "category_he": "בשר ודגים"},
            # ── Bakery / מאפים ──
            {"name": "Bread", "name_he": "לחם", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Pita", "name_he": "פיתה", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Challah", "name_he": "חלה", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Baguette", "name_he": "בגט", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Roll", "name_he": "לחמנייה", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Croissant", "name_he": "קרואסון", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Tortilla", "name_he": "טורטייה", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Laffa", "name_he": "לפה", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Cake", "name_he": "עוגה", "category": "Bakery", "category_he": "מאפים"},
            {"name": "Burekas", "name_he": "בורקס", "category": "Bakery", "category_he": "מאפים"},
            # ── Frozen / קפואים ──
            {"name": "Frozen Vegetables", "name_he": "ירקות קפואים", "category": "Frozen", "category_he": "קפואים"},
            {"name": "Ice Cream", "name_he": "גלידה", "category": "Frozen", "category_he": "קפואים"},
            {"name": "Frozen Pizza", "name_he": "פיצה קפואה", "category": "Frozen", "category_he": "קפואים"},
            {"name": "Frozen Schnitzel", "name_he": "שניצל קפוא", "category": "Frozen", "category_he": "קפואים"},
            # ── Beverages / משקאות ──
            {"name": "Water", "name_he": "מים", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Juice", "name_he": "מיץ", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Coffee", "name_he": "קפה", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Tea", "name_he": "תה", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Soda", "name_he": "סודה", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Cola", "name_he": "קולה", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Beer", "name_he": "בירה", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Wine", "name_he": "יין", "category": "Beverages", "category_he": "משקאות"},
            {"name": "Lemonade", "name_he": "לימונדה", "category": "Beverages", "category_he": "משקאות"},
            # ── Snacks / חטיפים ──
            {"name": "Chips", "name_he": "צ'יפס", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Bamba", "name_he": "במבה", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Bisli", "name_he": "ביסלי", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Crackers", "name_he": "קרקר", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Cookies", "name_he": "עוגיות", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Popcorn", "name_he": "פופקורן", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Nuts", "name_he": "אגוזים", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Chocolate", "name_he": "שוקולד", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Candy", "name_he": "סוכריות", "category": "Snacks", "category_he": "חטיפים"},
            {"name": "Pretzels", "name_he": "פריצל", "category": "Snacks", "category_he": "חטיפים"},
            # ── Pantry / מזווה ──
            {"name": "Rice", "name_he": "אורז", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Pasta", "name_he": "פסטה", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Flour", "name_he": "קמח", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Sugar", "name_he": "סוכר", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Oil", "name_he": "שמן", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Vinegar", "name_he": "חומץ", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Sauce", "name_he": "רוטב", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Canned Goods", "name_he": "שימורים", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Beans", "name_he": "שעועית", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Lentils", "name_he": "עדשים", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Hummus", "name_he": "חומוס", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Tahini", "name_he": "טחינה", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Soup", "name_he": "מרק", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Salt", "name_he": "מלח", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Black Pepper", "name_he": "פלפל שחור", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Paprika", "name_he": "פפריקה", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Turmeric", "name_he": "כורכום", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Cereal", "name_he": "קורנפלקס", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Tomato Paste", "name_he": "רסק עגבניות", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Ketchup", "name_he": "קטשופ", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Mustard", "name_he": "חרדל", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Mayonnaise", "name_he": "מיונז", "category": "Pantry", "category_he": "מזווה"},
            {"name": "Soy Sauce", "name_he": "סויה", "category": "Pantry", "category_he": "מזווה"},
            # ── Cleaning / ניקיון ──
            {"name": "Dish Soap", "name_he": "נוזל כלים", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Laundry Detergent", "name_he": "אבקת כביסה", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Fabric Softener", "name_he": "מרכך כביסה", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Bleach", "name_he": "אקונומיקה", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Sponge", "name_he": "ספוג", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Paper Towels", "name_he": "נייר מגבת", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Trash Bags", "name_he": "שקיות אשפה", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Wipes", "name_he": "מגבונים", "category": "Cleaning", "category_he": "ניקיון"},
            {"name": "Floor Cleaner", "name_he": "נוזל רצפה", "category": "Cleaning", "category_he": "ניקיון"},
            # ── Personal Care / טיפוח ──
            {"name": "Shampoo", "name_he": "שמפו", "category": "Personal Care", "category_he": "טיפוח"},
            {"name": "Toothpaste", "name_he": "משחת שיניים", "category": "Personal Care", "category_he": "טיפוח"},
            {"name": "Toothbrush", "name_he": "מברשת שיניים", "category": "Personal Care", "category_he": "טיפוח"},
            {"name": "Deodorant", "name_he": "דאודורנט", "category": "Personal Care", "category_he": "טיפוח"},
            {"name": "Body Lotion", "name_he": "קרם גוף", "category": "Personal Care", "category_he": "טיפוח"},
            {"name": "Toilet Paper", "name_he": "נייר טואלט", "category": "Personal Care", "category_he": "טיפוח"},
            {"name": "Tissues", "name_he": "טישו", "category": "Personal Care", "category_he": "טיפוח"},
            {"name": "Mouthwash", "name_he": "מי פה", "category": "Personal Care", "category_he": "טיפוח"},
            # ── Baby / תינוקות ──
            {"name": "Diapers", "name_he": "חיתולים", "category": "Baby", "category_he": "תינוקות"},
            {"name": "Baby Food", "name_he": "מזון תינוקות", "category": "Baby", "category_he": "תינוקות"},
            {"name": "Baby Wipes", "name_he": "מגבוני תינוקות", "category": "Baby", "category_he": "תינוקות"},
            {"name": "Baby Formula", "name_he": "תמ\"ל", "category": "Baby", "category_he": "תינוקות"},
            # ── Pet / חיות מחמד ──
            {"name": "Dog Food", "name_he": "מזון כלבים", "category": "Pet", "category_he": "חיות מחמד"},
            {"name": "Cat Food", "name_he": "מזון חתולים", "category": "Pet", "category_he": "חיות מחמד"},
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_global_items_name_he"), table_name="global_items")
    op.drop_index(op.f("ix_global_items_name"), table_name="global_items")
    op.drop_table("global_items")
