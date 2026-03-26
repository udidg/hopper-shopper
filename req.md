# Hopper Shopper — Telegram Bot for Grocery Lists

## Overview
A Telegram Bot for managing collaborative grocery lists in group chats. The bot listens to messages, parses grocery items, classifies them by store department, and sends beautified sorted lists — all in Hebrew. Supports natural language understanding via LLM (Gemini + Ollama fallback).

## Core Features
1. **Department Sorting:** `/sort` command classifies items by store department and sends a beautified, emoji-rich message
2. **Item Management:** Add, remove, and mark items as done via commands
3. **Auto-Detection:** Bot automatically detects multi-line grocery lists sent as free text
4. **Smart Classification:** Keyword-based + LLM fallback (Gemini primary, Ollama local) for department assignment
5. **Natural Language:** Understands Hebrew commands like "תוסיף חלב ולחם", "קניתי ביצים", "מה ברשימה?"
6. **Shopping Mode:** Interactive inline buttons to check off items while shopping
7. **Inline Suggestions:** Type `@bot_name` in any chat to get item suggestions from history
8. **Item Details:** Save default brand/details per item with `/detail` (auto-applied on future adds)
9. **Price Tracking:** Track last observed prices for items
10. **Hebrew-First:** All UI text and department names are in Hebrew

## Bot Commands
| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Show available commands (Hebrew) |
| `/add item1, item2` | Add items to the list |
| `/remove item` | Remove an item |
| `/clear` | Clear the entire list |
| `/done item` | Mark item as purchased |
| `/undone item` | Unmark item |
| `/list` | Show current list (unsorted) |
| `/sort` | Show list sorted by department |
| `/detail item details` | Save default brand/details for an item |
| `/price item 7.90` | Set item price |
| `/shop` | Interactive shopping mode with buttons |

## Technology Stack
- **Bot Framework:** python-telegram-bot v21+ (async)
- **Database:** PostgreSQL 16 + async SQLAlchemy 2.x + Alembic
- **LLM (optional):** Gemini API (primary, cloud) + Ollama (fallback, local)
- **HTTP Client:** httpx (async, connection pooling)
- **Settings:** pydantic-settings
- **Containerization:** Docker + Docker Compose

## Project Structure
```
hopper-shopper/
├── bot/
│   ├── main.py              # Entry point, lifecycle hooks
│   ├── config.py             # Settings from env vars
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

## Deployment
```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and DB credentials

# 2. Start services
docker compose up -d

# Optional: Enable local LLM classification
docker compose --profile ollama up -d
```
