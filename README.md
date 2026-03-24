# 🛒 Hopper Shopper

A Telegram Bot for managing collaborative grocery lists in group chats.
Send items, sort them by store department, and shop interactively — all in Hebrew.

## Features

- **🏪 Department Sorting** — `/sort` classifies items by store department with emojis
- **📝 Item Management** — Add, remove, and mark items as done
- **🔍 Auto-Detection** — Bot detects multi-line grocery lists sent as free text
- **🧠 Smart Classification** — Keyword-based + optional LLM (Ollama) fallback
- **🛍️ Shopping Mode** — Interactive inline buttons to check off items while shopping
- **💰 Price Tracking** — Track last observed prices for items
- **🇮🇱 Hebrew-First** — All UI text and department names are in Hebrew

## Bot Commands

| Command | Description |
|---------|-------------|
| `/add פריט1, פריט2` | הוספת פריטים לרשימה |
| `/remove פריט` | הסרת פריט מהרשימה |
| `/list` | הצגת הרשימה הנוכחית |
| `/sort` | מיון הרשימה לפי מחלקות |
| `/done פריט` | סימון פריט כנקנה |
| `/undone פריט` | ביטול סימון פריט |
| `/clear` | ניקוי כל הרשימה |
| `/shop` | מצב קניות עם כפתורים אינטראקטיביים |
| `/price פריט מחיר` | עדכון מחיר פריט |
| `/help` | עזרה |

## Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env — set TELEGRAM_BOT_TOKEN and POSTGRES_PASSWORD

# 2. Run
docker compose up -d

# 3. Check logs
docker compose logs -f bot
```

## Example

Send a message in a group chat:
```
חלב
עגבניות
שניצל
לחם
אקונומיקה
במבה
```

The bot auto-detects it as a grocery list. Then send `/sort`:

```
🛒 רשימת קניות

🥬 ירקות ופירות
  • עגבניות

🧀 מוצרי חלב
  • חלב

🥩 בשר ודגים
  • שניצל

🍞 מאפים
  • לחם

🍿 חטיפים
  • במבה

🧹 ניקיון
  • אקונומיקה

📊 6 פריטים
```

## Tech Stack

- **Bot Framework:** [python-telegram-bot](https://python-telegram-bot.org/) v21+ (async)
- **Database:** PostgreSQL + async SQLAlchemy 2.x + Alembic
- **LLM (optional):** [Ollama](https://ollama.ai/) for smart department classification
- **Containerization:** Docker + Docker Compose

## Project Structure

```
hopper-shopper/
├── bot/
│   ├── main.py              # Entry point
│   ├── config.py             # Settings from env vars
│   ├── database.py           # Async SQLAlchemy session
│   ├── handlers/
│   │   ├── commands.py       # /add, /sort, /list, etc.
│   │   ├── messages.py       # Free-text auto-detection
│   │   ├── callbacks.py      # Shopping mode buttons
│   │   └── inline.py         # Inline query suggestions
│   ├── services/
│   │   ├── grouping.py       # Department classification
│   │   ├── llm.py            # Ollama integration
│   │   ├── formatter.py      # Hebrew message formatting
│   │   ├── parser.py         # Text → item list parsing
│   │   └── list_manager.py   # DB CRUD operations
│   └── models/
│       ├── user.py
│       ├── grocery_list.py
│       ├── grocery_item.py
│       └── item_history.py
├── alembic/                  # DB migrations
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Deployment

See [plans/deployment-guide.md](plans/deployment-guide.md) for full deployment instructions including NAS upgrade path.

## License

MIT
