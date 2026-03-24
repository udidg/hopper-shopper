# Hopper Shopper Bot — Deployment Guide

## Upgrading from the Mini App

Since the bot replaces the old Telegram Mini App that was already deployed on your NAS, this guide covers the upgrade path.

---

## Step 1: Set Up BotFather (if not already done)

If your bot is already created in BotFather, just update the commands:

1. Open Telegram → **@BotFather**
2. Send `/setcommands`, select your bot, paste:
   ```
   add - הוספת פריטים לרשימה
   remove - הסרת פריט מהרשימה
   list - הצגת הרשימה
   sort - מיון לפי מחלקות
   done - סימון פריט כנקנה
   undone - ביטול סימון
   clear - ניקוי הרשימה
   shop - מצב קניות אינטראקטיבי
   price - עדכון מחיר פריט
   help - עזרה
   ```
3. Send `/setinline`, select your bot, set placeholder: `חפש פריט...`
4. Send `/setprivacy`, select your bot, choose **Disable** (so the bot reads group messages for auto-detection)

---

## Step 2: Deploy to NAS

SSH into your NAS and navigate to the project directory:

```bash
cd /path/to/hopper-shopper
```

### Stop the old services:
```bash
docker compose down
```

> **Note:** This does NOT delete the PostgreSQL data volume. Your existing database is preserved.

### Update `.env`:

The `.env` file is simplified — you can keep the existing values. The only required variables are:

```env
# Keep your existing bot token
TELEGRAM_BOT_TOKEN=your_existing_bot_token

# Keep your existing DB credentials
POSTGRES_USER=hopper
POSTGRES_PASSWORD=your_existing_password
POSTGRES_DB=hopper_shopper
DATABASE_URL=postgresql+asyncpg://hopper:your_existing_password@db:5432/hopper_shopper

# Optional: Ollama LLM
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=gemma3:1b
```

You can remove these old variables (no longer needed):
- `SECRET_KEY`
- `CORS_ORIGINS`
- `BACKEND_PORT`
- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`
- `SSL_CERT_PATH`
- `SSL_KEY_PATH`
- `DOMAIN`

### Copy the new docker-compose.yml:
```bash
# Get the latest docker-compose.yml from the repo
curl -o docker-compose.yml https://raw.githubusercontent.com/udidg/hopper-shopper/main/docker-compose.yml
```

### Start the new bot:
```bash
docker compose pull
docker compose up -d
```

### Verify it's running:
```bash
docker compose logs -f bot
```

You should see:
```
=== Hopper Shopper Bot ===
Checking for old migration state...
  Found old migration: a4b5ccd70ffc — resetting...
  Old migration state cleared.
Running database migrations...
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_bot, Migrate from Mini App schema to Bot schema
Starting Hopper Shopper bot...
INFO - Starting Hopper Shopper bot...
INFO - Bot is ready! Starting polling...
```

The migration automatically:
- Adds `chat_id` and `is_active` to `grocery_lists`
- Renames `is_scratched` → `is_done` in `grocery_items`
- Creates the `item_history` table
- Drops unused tables (`list_members`, `item_dictionary`, `global_items`)

---

## Step 3: Test

1. Open your bot in Telegram and send `/start`
2. Send `/help` to see the command list
3. Add the bot to a group chat
4. Send `/add חלב, לחם, ביצים`
5. Send `/sort` to see the sorted list
6. Send `/shop` for interactive shopping mode

---

## Optional: Enable Ollama LLM

```bash
docker compose --profile llm up -d
docker compose exec ollama ollama pull gemma3:1b
```

---

## Maintenance

| Task | Command |
|------|---------|
| View logs | `docker compose logs -f bot` |
| Restart bot | `docker compose restart bot` |
| Update to latest | `docker compose pull && docker compose up -d` |
| DB backup | `docker compose exec db pg_dump -U hopper hopper_shopper > backup.sql` |
| DB restore | `cat backup.sql \| docker compose exec -T db psql -U hopper hopper_shopper` |

> **Note:** The bot image is automatically built and pushed to Docker Hub by GitHub Actions on every push to `main`. Just `docker compose pull` on your NAS to get the latest version.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Bot doesn't respond | `docker compose logs bot` — check for errors |
| "Database error" messages | `docker compose logs db` — is PostgreSQL healthy? |
| Bot doesn't read group messages | BotFather → `/setprivacy` → **Disable** |
| Inline suggestions don't work | BotFather → `/setinline` → set a placeholder |
| Migration fails | Check `docker compose logs bot` for the specific error |
| Old containers still running | `docker compose down` then `docker compose up -d --build` |
