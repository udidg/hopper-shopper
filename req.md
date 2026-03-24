# Hopper Shopper — Telegram Bot for Grocery Lists

## Overview
A pure Telegram Bot for managing collaborative grocery lists in group chats. The bot listens to messages, parses grocery items, classifies them by store department, and sends beautified sorted lists — all in Hebrew.

## Core Features
1. **Department Sorting:** `/sort` command classifies items by store department and sends a beautified, emoji-rich message
2. **Item Management:** Add, remove, and mark items as done via commands
3. **Auto-Detection:** Bot automatically detects multi-line grocery lists sent as free text
4. **Smart Classification:** Keyword-based + optional LLM (Ollama) fallback for department assignment
5. **Shopping Mode:** Interactive inline buttons to check off items while shopping
6. **Inline Suggestions:** Type `@bot_name` in any chat to get item suggestions from history
7. **Price Tracking:** Track last observed prices for items
8. **Hebrew-First:** All UI text and department names are in Hebrew

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
| `/price item 7.90` | Set item price |
| `/shop` | Interactive shopping mode with buttons |

## Technology Stack
- **Bot Framework:** python-telegram-bot v21+ (async)
- **Database:** PostgreSQL + async SQLAlchemy 2.x + Alembic
- **LLM (optional):** Ollama for smart department classification
- **Containerization:** Docker + Docker Compose

## Project Structure
```
hopper-shopper/
├── bot/
│   ├── main.py              # Entry point
│   ├── config.py             # Settings from env vars
│   ├── database.py           # Async SQLAlchemy session
│   ├── handlers/             # Telegram update handlers
│   │   ├── commands.py       # /add, /sort, /list, etc.
│   │   ├── messages.py       # Free-text auto-detection
│   │   ├── callbacks.py      # Shopping mode buttons
│   │   └── inline.py         # Inline query suggestions
│   ├── services/             # Business logic
│   │   ├── grouping.py       # Department classification
│   │   ├── llm.py            # Ollama integration
│   │   ├── formatter.py      # Hebrew message formatting
│   │   ├── parser.py         # Text → item list parsing
│   │   └── list_manager.py   # DB CRUD operations
│   └── models/               # SQLAlchemy models
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
```bash
# 1. Copy and configure environment
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and DB credentials

# 2. Start services
docker compose up -d

# Optional: Enable LLM classification
docker compose --profile llm up -d
```
