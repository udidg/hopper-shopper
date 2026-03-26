# Hopper Shopper Bot — Deployment Guide

This guide covers deploying the Hopper Shopper Telegram bot to a NAS (or any Docker host). It handles both fresh installations and upgrades from the previous Mini App version.

## CI/CD Pipeline

Every push to `main` triggers a GitHub Actions workflow that builds the Docker image and pushes it to Docker Hub as `udidg/hopper-shopper-bot:latest`. The NAS pulls this pre-built image — no local builds required.

---

## Prerequisites

- Docker and Docker Compose installed on the NAS
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- SSH access to the NAS

---

## Step 1: Configure BotFather

Open Telegram and message **@BotFather**:

1. **Create a bot** (skip if already done):
   - Send `/newbot`, choose a name and username
   - Save the bot token

2. **Set commands** — send `/setcommands`, select your bot, paste:
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

3. **Enable inline mode** — send `/setinline`, select your bot, set placeholder: `חפש פריט...`

4. **Disable privacy mode** — send `/setprivacy`, select your bot, choose **Disable**
   > This allows the bot to read all group messages so it can auto-detect grocery lists.

---

## Step 2: Prepare the NAS

SSH into your NAS:

```bash
ssh user@your-nas-ip
```

### For upgrades from the Mini App:

```bash
cd /path/to/hopper-shopper

# Stop old services (database volume is preserved)
docker compose down
```

### For fresh installations:

```bash
mkdir -p /path/to/hopper-shopper
cd /path/to/hopper-shopper
```

---

## Step 3: Create Configuration Files

### `docker-compose.yml`

Download the latest compose file:

```bash
curl -o docker-compose.yml \
  https://raw.githubusercontent.com/udidg/hopper-shopper/main/docker-compose.yml
```

### `.env`

Create the environment file:

```bash
cat > .env << 'EOF'
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database
POSTGRES_USER=hopper
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=hopper_shopper
DATABASE_URL=postgresql+asyncpg://hopper:your_secure_password@db:5432/hopper_shopper

# Optional: Ollama LLM for smart department classification
# OLLAMA_URL=http://ollama:11434
# OLLAMA_MODEL=gemma3:1b
EOF
```

Edit the file and set your actual values:

```bash
nano .env
```

> **Upgrading?** Keep your existing `TELEGRAM_BOT_TOKEN` and database credentials. You can remove old variables like `SECRET_KEY`, `CORS_ORIGINS`, `VITE_*`, `SSL_*`, and `DOMAIN` — they are no longer needed.

---

## Step 4: Start the Bot

```bash
docker compose pull
docker compose up -d
```

Check the logs to verify everything started correctly:

```bash
docker compose logs -f bot
```

Expected output:

```
=== Hopper Shopper Bot ===
Checking for old migration state...
Running database migrations...
INFO  [alembic.runtime.migration] Running upgrade -> 001_initial_bot
Starting Hopper Shopper bot...
INFO - Starting Hopper Shopper bot...
INFO - Bot is ready! Starting polling...
```

> **Upgrading?** The migration automatically adapts the existing database: adds `chat_id` to lists, renames `is_scratched` → `is_done`, creates the `item_history` table, and drops unused tables (`list_members`, `item_dictionary`, `global_items`).

---

## Step 5: Verify

1. Open Telegram and message your bot
2. Send `/start` — you should get a welcome message
3. Send `/add חלב, לחם, ביצים` — items should be added
4. Send `/sort` — items should appear sorted by department
5. Add the bot to a group chat and send a multi-line grocery list — the bot should auto-detect it

---

## Optional: Enable Smart Classification (Ollama)

For items not in the keyword dictionary, enable LLM-based classification:

```bash
# Uncomment OLLAMA_URL and OLLAMA_MODEL in .env, then:
docker compose --profile llm up -d

# Pull the model (first time only, ~1GB download)
docker compose exec ollama ollama pull gemma3:1b
```

---

## Updating

The bot image is automatically built and pushed to Docker Hub on every push to `main`. To update your NAS deployment:

```bash
docker compose pull
docker compose up -d
```

---

## Maintenance

| Task | Command |
|------|---------|
|Pull latest docker-compose file|curl -o docker-compose.yml https://raw.githubusercontent.com/udidg/hopper-shopper/main/docker-compose.yml|
| View logs | `docker compose logs -f bot` |
| Restart bot | `docker compose restart bot` |
| Update to latest | `docker compose pull && docker compose up -d` |
| Backup database | `docker compose exec db pg_dump -U hopper hopper_shopper > backup.sql` |
| Restore database | `cat backup.sql \| docker compose exec -T db psql -U hopper hopper_shopper` |
| Stop everything | `docker compose down` |
| Full reset (⚠️) | `docker compose down -v` (deletes database!) |

---

## Troubleshooting

| Symptom | Cause & Fix |
|---------|-------------|
| Bot doesn't respond to messages | Check logs: `docker compose logs bot`. Verify `TELEGRAM_BOT_TOKEN` is correct in `.env`. |
| "שגיאה בגישה למסד הנתונים" errors | Database may be unhealthy: `docker compose logs db`. Try `docker compose restart db`. |
| Bot ignores messages in groups | Privacy mode is enabled. Send `/setprivacy` → **Disable** to BotFather. |
| Inline suggestions don't appear | Inline mode not enabled. Send `/setinline` to BotFather and set a placeholder. |
| Migration fails on startup | Check `docker compose logs bot` for the specific SQL error. Ensure the database is accessible. |
| Container keeps restarting | Check logs for Python errors. Common cause: missing or invalid `TELEGRAM_BOT_TOKEN`. |
| Items not classified into departments | Item may not be in the keyword dictionary. Enable Ollama for smarter classification. |
