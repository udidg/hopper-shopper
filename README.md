# 🛒 Hopper Shopper

A Telegram Bot for managing collaborative grocery lists in group chats.
Send items, sort them by store department, and shop interactively — all in Hebrew.

## Features

- **🏪 Department Sorting** — `/sort` classifies items by store department with emojis
- **📝 Item Management** — Add, remove, and mark items as done
- **🔍 Auto-Detection** — Bot detects multi-line grocery lists sent as free text
- **🧠 Smart Classification** — Keyword-based + LLM fallback (Gemini primary, Ollama local)
- **🗣️ Natural Language** — Understands Hebrew commands like "תוסיף חלב ולחם" or "קניתי ביצים"
- **🛍️ Shopping Mode** — Interactive inline buttons to check off items while shopping
- **💰 Price Tracking** — Track last observed prices for items
- **📋 Item Details** — Save default brand/details per item (auto-applied on future adds)
- **🔎 Inline Suggestions** — Type `@bot_name` to get item suggestions from your history
- **🇮🇱 Hebrew-First** — All UI text and department names are in Hebrew

## Bot Commands

| Command | Description |
|---------|-------------|
| `/add פריט1, פריט2` | הוספת פריטים לרשימה |
| `/remove פריט` | הסרת פריט מהרשימה |
| `/list` | הצגת הרשימה הנוכחית (עם הצעות מהיסטוריה כשריקה) |
| `/sort` | מיון הרשימה לפי מחלקות |
| `/done פריט` | סימון פריט כנקנה |
| `/undone פריט` | ביטול סימון פריט |
| `/clear` | ניקוי כל הרשימה (עם אישור) |
| `/cleardone` | ניקוי רק פריטים שנקנו |
| `/shop` | מצב קניות עם כפתורים אינטראקטיביים |
| `/detail פריט פרטים` | שמירת מותג/פרטים לפריט |
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

The bot auto-detects it as a grocery list and **automatically shows the sorted view**:

```
✅ 6 פריטים נוספו לרשימה:
  • חלב
  • עגבניות
  • שניצל
  • לחם
  • אקונומיקה
  • במבה

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

## UX Highlights

- **🔄 Auto-Sort** — When you send a multi-item grocery list, the bot adds items AND shows the sorted view automatically
- **⌨️ Typing Indicator** — Bot shows "typing..." during LLM processing so you know it's working
- **⚠️ Safe Clear** — `/clear` asks for confirmation before deleting; offers to clear only purchased items
- **🧹 Clear Done** — `/cleardone` removes only purchased items, keeping your pending list intact
- **📝 Smart Empty State** — When the list is empty, `/list` suggests your most frequently bought items as quick-add buttons
- **🎉 Shopping Completion** — When all items are checked off in `/shop`, shows a summary with cleanup actions

## Tech Stack

- **Bot Framework:** [python-telegram-bot](https://python-telegram-bot.org/) v21+ (async)
- **Database:** PostgreSQL 16 + async SQLAlchemy 2.x + Alembic
- **LLM (optional):** [Gemini API](https://aistudio.google.com/apikey) (primary) + [Ollama](https://ollama.ai/) (local fallback)
- **HTTP Client:** httpx (async, connection pooling)
- **Containerization:** Docker + Docker Compose

## Project Structure

```
hopper-shopper/
├── bot/
│   ├── main.py              # Entry point, lifecycle hooks
│   ├── config.py             # Settings from env vars (pydantic-settings)
│   ├── database.py           # Async SQLAlchemy engine & session
│   ├── handlers/
│   │   ├── commands.py       # /add, /sort, /list, /detail, etc.
│   │   ├── messages.py       # Free-text auto-detection + NLU
│   │   ├── callbacks.py      # Shopping mode buttons
│   │   └── inline.py         # Inline query suggestions
│   ├── services/
│   │   ├── grouping.py       # Department classification (keyword maps)
│   │   ├── llm.py            # Gemini + Ollama LLM integration
│   │   ├── formatter.py      # Hebrew message formatting
│   │   ├── parser.py         # Text → item list parsing
│   │   └── list_manager.py   # DB CRUD operations
│   ├── models/
│   │   ├── user.py
│   │   ├── grocery_list.py
│   │   ├── grocery_item.py
│   │   └── item_history.py
│   └── utils/
│       └── db.py             # DB session helper with retry logic
├── alembic/                  # DB migrations
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh
├── requirements.txt
└── .env.example
```

## Architecture & Resilience

The bot is designed for production reliability:

- **Database:** Connection pooling with `pool_pre_ping` (stale connection detection), automatic retry on transient errors, bulk operations
- **LLM:** Circuit breaker pattern (skips failing backends for 60s cooldown), shared HTTP client with connection pooling, bounded LRU cache (2000 entries), global rate limiting
- **Handlers:** Null-safe guards on all Telegram update fields, user-facing error messages on all failures, input validation
- **Data Integrity:** Unique constraints prevent duplicate lists and history entries, Unicode-normalized item names, LIKE-pattern escaping
- **Infrastructure:** Health checks on all containers, resource limits, graceful shutdown with proper cleanup, DB readiness wait loop on startup

## Environment Variables

See [`.env.example`](.env.example) for all available settings:

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from [@BotFather](https://t.me/BotFather) |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `GEMINI_API_KEY` | ❌ | Google AI Studio API key (free tier available) |
| `GEMINI_MODEL` | ❌ | Gemini model name (default: `gemini-2.0-flash`) |
| `OLLAMA_URL` | ❌ | Ollama server URL (default: empty) |
| `OLLAMA_MODEL` | ❌ | Ollama model name (default: `gemma3:1b`) |
| `LLM_RATE_LIMIT` | ❌ | Max LLM requests/minute (default: `20`) |
| `LOG_LEVEL` | ❌ | Logging level (default: `INFO`) |

## Deployment

See [plans/deployment-guide.md](plans/deployment-guide.md) for full deployment instructions including NAS upgrade path.

## License

MIT
