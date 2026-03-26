# 🛡️ Hopper Shopper — Robustness & Resilience Plan

## Executive Summary

After a thorough review of the entire codebase, I've identified **27 issues** across 7 categories that affect reliability, error resilience, and correctness. This plan addresses each one with specific, actionable fixes.

---

## Issues Found & Fixes

### 1. Database Connection Resilience

#### 1.1 No connection pool configuration
**File:** `bot/database.py`  
**Problem:** The SQLAlchemy engine is created with no pool settings. Under load or after DB restarts, connections can go stale, causing cascading failures.  
**Fix:** Add pool configuration with `pool_size`, `max_overflow`, `pool_pre_ping=True` (validates connections before use), and `pool_recycle` (prevents stale connections).

#### 1.2 No retry logic on transient DB errors
**File:** `bot/handlers/commands.py`, `bot/handlers/callbacks.py`, `bot/handlers/messages.py`  
**Problem:** Every handler wraps DB calls in a bare `try/except Exception` that logs and returns an error message. If the DB has a momentary hiccup (connection reset, brief overload), the user gets an error with no retry.  
**Fix:** Create a reusable `db_session` context manager/decorator with automatic retry (1-2 retries with short backoff) for `OperationalError` / `DisconnectionError`. This eliminates the repetitive try/except boilerplate across all handlers.

#### 1.3 Engine disposal not handled on shutdown
**File:** `bot/database.py`, `bot/main.py`  
**Problem:** The async engine is never disposed on shutdown, potentially leaving dangling connections.  
**Fix:** Add a `post_shutdown` hook to the Application builder that calls `await engine.dispose()`.

---

### 2. Handler Error Handling & Edge Cases

#### 2.1 NoneType crashes on `update.message`
**Files:** `bot/handlers/commands.py` (all command handlers)  
**Problem:** Every command handler accesses `update.message.text` and `update.message.reply_text()` without null checks. In edge cases (edited messages, channel posts), `update.message` can be `None`, causing `AttributeError` crashes.  
**Fix:** Add a guard at the top of each handler: `if not update.message: return`. Better yet, create a decorator that handles this.

#### 2.2 NoneType crash on `update.effective_user` / `update.effective_chat`
**File:** `bot/handlers/commands.py` → `_get_user_and_list()`  
**Problem:** `update.effective_user` and `update.effective_chat` are accessed without null checks. In rare Telegram API edge cases these can be `None`.  
**Fix:** Add null checks and early return with a user-friendly message.

#### 2.3 `handle_shop_callback` double-answers on error
**File:** `bot/handlers/callbacks.py:69`  
**Problem:** `await query.answer()` is called unconditionally at line 69, then `query.answer()` is called again at line 101 if the item is not found. Telegram's API will reject the second answer, causing a `BadRequest` exception.  
**Fix:** Remove the early `query.answer()` and only answer once per code path, or use a flag.

#### 2.4 Silent failures in message handler
**File:** `bot/handlers/messages.py` → `_handle_add_action()`, `_handle_remove_action()`, etc.  
**Problem:** When DB operations fail, these functions log the error but **never notify the user**. The user sends a message and gets no response at all — they think the bot is dead.  
**Fix:** Add `await update.message.reply_text(DB_ERROR_MSG)` in the except blocks of all `_handle_*` action functions.

#### 2.5 `edit_message_text` can raise `BadRequest` for unchanged content
**File:** `bot/handlers/callbacks.py:131-137`  
**Problem:** If the user taps the same button twice quickly, the message content hasn't changed, and `edit_message_text` raises `BadRequest: Message is not modified`. The bare `except Exception: pass` silently swallows ALL exceptions including real bugs.  
**Fix:** Catch specifically `telegram.error.BadRequest` and only suppress the "not modified" variant.

---

### 3. LLM Service Resilience

#### 3.1 httpx client created per-request
**File:** `bot/services/llm.py` → `_gemini_generate()`, `_ollama_generate()`  
**Problem:** A new `httpx.AsyncClient` is created and destroyed for every single LLM call. This means a new TCP connection + TLS handshake for every request — slow and wasteful.  
**Fix:** Create a module-level shared `httpx.AsyncClient` with connection pooling, and close it on shutdown.

#### 3.2 Rate limiter lock is not process-safe
**File:** `bot/services/llm.py:46-73`  
**Problem:** The `asyncio.Lock` and in-memory deque are only valid within a single process. If the bot is ever scaled to multiple workers, rate limiting breaks. This is a minor concern for now but worth noting.  
**Fix:** Document this limitation. For single-process deployment (current), this is fine.

#### 3.3 Classification cache grows unbounded
**File:** `bot/services/llm.py:84-85`  
**Problem:** `_classification_cache` is a plain dict that grows forever. Over months of operation with thousands of unique items, this becomes a memory leak.  
**Fix:** Use an LRU cache with a max size (e.g., `functools.lru_cache` or a simple bounded dict). Alternatively, add periodic cleanup of entries older than `_CACHE_TTL`.

#### 3.4 Gemini API key exposed in URL
**File:** `bot/services/llm.py:146-147`  
**Problem:** The API key is passed as a query parameter in the URL. If any HTTP error logging includes the full URL, the key gets logged in plaintext.  
**Fix:** Use the `x-goog-api-key` header instead of the URL query parameter for Gemini API authentication.

#### 3.5 No circuit breaker for LLM backends
**File:** `bot/services/llm.py`  
**Problem:** If Gemini is down, every request still tries Gemini first (and waits for timeout) before falling back to Ollama. This adds 15s latency to every request during an outage.  
**Fix:** Implement a simple circuit breaker: after N consecutive failures, skip Gemini for a cooldown period (e.g., 60s) and go straight to Ollama.

---

### 4. Data Integrity & Database Issues

#### 4.1 No unique constraint on `(chat_id, is_active)` for grocery lists
**File:** `bot/models/grocery_list.py`  
**Problem:** `get_or_create_active_list()` uses `scalar_one_or_none()` which will throw `MultipleResultsFound` if a race condition creates two active lists for the same chat. This is a real risk in group chats with concurrent users.  
**Fix:** Add a partial unique index: `CREATE UNIQUE INDEX ON grocery_lists (chat_id) WHERE is_active = true`. This guarantees at most one active list per chat at the database level.

#### 4.2 No unique constraint on `(chat_id, name)` for item history
**File:** `bot/models/item_history.py`  
**Problem:** `_upsert_item_history()` does a SELECT then INSERT, which is not atomic. Two concurrent adds of the same item can create duplicate history entries, and subsequent lookups with `scalar_one_or_none()` will crash with `MultipleResultsFound`.  
**Fix:** Add a unique constraint on `(chat_id, name)` to `item_history` and use `INSERT ... ON CONFLICT` (or handle `IntegrityError` with a retry).

#### 4.3 `ilike` matching can return wrong items
**File:** `bot/services/list_manager.py` (multiple functions)  
**Problem:** `GroceryItem.name.ilike(name)` without wildcards does exact case-insensitive match, which is correct. However, if the user types extra whitespace or has different Unicode normalization, the match fails silently. Also, `remove_items` only removes the first match — if there are duplicates, the rest remain.  
**Fix:** Normalize item names on insert (strip, normalize Unicode). For `remove_items`, use `.all()` instead of `.scalar_one_or_none()` to remove all matches.

#### 4.4 `clear_list` deletes items one-by-one
**File:** `bot/services/list_manager.py:317-329`  
**Problem:** Items are loaded into memory and deleted one at a time in a loop. For large lists, this is N+1 queries.  
**Fix:** Use a bulk `DELETE FROM grocery_items WHERE list_id = :id` statement instead.

---

### 5. Infrastructure & Docker

#### 5.1 No health check for the bot container
**File:** `docker-compose.yml`  
**Problem:** The `db` service has a health check, but the `bot` service does not. Docker/orchestrators can't tell if the bot process is alive and healthy.  
**Fix:** Add a health check. Options: (a) write a small health file periodically and check it, or (b) add a simple HTTP health endpoint using `python-telegram-bot`'s webhook capabilities, or (c) use a process-based check.

#### 5.2 No resource limits on containers
**File:** `docker-compose.yml`  
**Problem:** No memory or CPU limits. A memory leak or runaway LLM call could consume all host resources.  
**Fix:** Add `deploy.resources.limits` for both `bot` and `db` services.

#### 5.3 No logging configuration for production
**File:** `bot/main.py`  
**Problem:** Logging goes to stdout with no structured format, no log rotation, and no log level configuration via environment variable.  
**Fix:** Add a `LOG_LEVEL` env var to `Settings`, use structured JSON logging for production, and configure log levels per-module.

#### 5.4 Entrypoint script error handling
**File:** `entrypoint.sh`  
**Problem:** The inline Python script for checking migration state redirects stderr to `/dev/null` (`2>/dev/null`), hiding real errors. If the DB connection fails during this check, the error is silently swallowed, and the script continues to `alembic upgrade head` which will also fail — but with a confusing error message.  
**Fix:** Remove `2>/dev/null`, let errors propagate, and add a DB readiness wait loop before running migrations.

#### 5.5 `sys.exit(1)` in error handler is not graceful
**File:** `bot/main.py:97-98`  
**Problem:** `asyncio.get_event_loop().call_soon(lambda: sys.exit(1))` is used to shut down on repeated 409 conflicts. `sys.exit()` raises `SystemExit` which may not cleanly shut down the async event loop, database connections, or pending tasks.  
**Fix:** Use `application.stop()` or set a flag that triggers graceful shutdown through the proper `python-telegram-bot` shutdown mechanism.

---

### 6. Inline Query Security

#### 6.1 SQL injection via inline query
**File:** `bot/handlers/inline.py:48`  
**Problem:** `ItemHistory.name.ilike(f"%{search_text}%")` — the `search_text` comes directly from user input. While SQLAlchemy parameterizes queries (so actual SQL injection is prevented), the `%` and `_` characters in LIKE patterns are not escaped. A user could send `%` to match all items across all chats.  
**Fix:** Escape LIKE special characters (`%` → `\%`, `_` → `\_`) in the search text.

#### 6.2 Inline query searches across ALL chats
**File:** `bot/handlers/inline.py:38-51`  
**Problem:** The comment says "we search across all chats" — this means any user can see item names from ANY chat's history. This is a privacy leak.  
**Fix:** Filter by chats the user has interacted with. Store a `user_id` or `telegram_user_id` on `ItemHistory`, or maintain a user-chat mapping table.

---

### 7. Code Quality & Maintainability

#### 7.1 Imports inside functions
**File:** `bot/handlers/callbacks.py:93-94`, `bot/handlers/commands.py:369-371`, `bot/handlers/messages.py:195,228,289`  
**Problem:** Multiple handlers import models and services inside function bodies. This hides dependencies and can cause import errors to surface at runtime instead of startup.  
**Fix:** Move all imports to the top of each file.

#### 7.2 Duplicated user/list boilerplate
**Files:** All handler files  
**Problem:** The pattern `get_or_create_user() → get_or_create_active_list()` is repeated ~15 times across handlers. Each copy has the same null-safety risks.  
**Fix:** Extract into a single utility function or decorator that provides `(session, user, grocery_list)` to the handler.

#### 7.3 No input validation on callback data
**File:** `bot/handlers/callbacks.py:85`  
**Problem:** `item_id = int(parts[2])` — if a malicious user crafts a callback with a very large number, this could cause issues. The `ValueError` is caught, but there's no upper bound check.  
**Fix:** Add a reasonable upper bound check on `item_id`.

---

## Implementation Priority

### Phase 1: Critical Fixes (Prevent crashes & data corruption)
1. Add null checks on `update.message`, `update.effective_user`, `update.effective_chat` (2.1, 2.2)
2. Fix silent failures in message handlers — always notify user on error (2.4)
3. Add unique constraints to prevent duplicate lists/history entries (4.1, 4.2)
4. Fix double-answer in shop callback (2.3)
5. Fix inline query privacy leak (6.2)
6. Fix `edit_message_text` exception swallowing (2.5)

### Phase 2: Resilience (Survive infrastructure issues)
7. Add DB connection pool configuration with `pool_pre_ping` (1.1)
8. Create reusable DB session helper with retry logic (1.2)
9. Add engine disposal on shutdown (1.3)
10. Add circuit breaker for LLM backends (3.5)
11. Move to shared httpx client (3.1)
12. Bound the classification cache (3.3)
13. Fix Gemini API key exposure in URL (3.4)

### Phase 3: Infrastructure Hardening
14. Add bot container health check (5.1)
15. Add resource limits to docker-compose (5.2)
16. Fix entrypoint error handling (5.4)
17. Fix graceful shutdown mechanism (5.5)
18. Add configurable log level (5.3)

### Phase 4: Code Quality
19. Move inline imports to top of files (7.1)
20. Extract user/list boilerplate into shared utility (7.2)
21. Escape LIKE wildcards in inline search (6.1)
22. Bulk delete in `clear_list` (4.4)
23. Normalize item names on insert (4.3)
24. Add input validation on callback data (7.3)

### Phase 5: New Alembic Migration
25. Create migration `004_add_unique_constraints.py` for the new DB constraints (4.1, 4.2)

---

## Architecture Diagram

```mermaid
flowchart TD
    subgraph Telegram
        U[User Message]
    end

    subgraph Bot Process
        U --> MH[Message Handler]
        U --> CH[Command Handler]
        U --> CB[Callback Handler]
        U --> IQ[Inline Query Handler]

        MH --> GRD[Guard: null checks + input validation]
        CH --> GRD
        CB --> GRD
        IQ --> GRD

        GRD --> DBS[DB Session Helper - retry + pool_pre_ping]
        DBS --> LM[List Manager - CRUD]
        LM --> PG[(PostgreSQL - with unique constraints)]

        MH --> LLM_SVC[LLM Service]
        LLM_SVC --> CB_BREAKER[Circuit Breaker]
        CB_BREAKER --> GEMINI[Gemini API - header auth]
        CB_BREAKER --> OLLAMA[Ollama - local fallback]
        LLM_SVC --> CACHE[Bounded LRU Cache]
    end

    subgraph Infrastructure
        PG
        GEMINI
        OLLAMA
        HC[Health Check] --> Bot Process
    end
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `bot/database.py` | Pool config, shared engine disposal helper |
| `bot/main.py` | Shutdown hooks, graceful exit, log level config |
| `bot/config.py` | Add `LOG_LEVEL` setting |
| `bot/handlers/commands.py` | Null guards, use shared DB helper, top-level imports |
| `bot/handlers/callbacks.py` | Fix double-answer, specific exception catch, top-level imports |
| `bot/handlers/messages.py` | User error notifications, top-level imports |
| `bot/handlers/inline.py` | Privacy fix, LIKE escaping |
| `bot/services/llm.py` | Shared httpx client, circuit breaker, bounded cache, header auth |
| `bot/services/list_manager.py` | Bulk delete, name normalization, handle duplicates |
| `bot/models/item_history.py` | Add unique constraint metadata |
| `docker-compose.yml` | Bot health check, resource limits |
| `entrypoint.sh` | Remove stderr suppression, add DB wait loop |
| `alembic/versions/004_add_unique_constraints.py` | New migration for unique constraints |

## New Files

| File | Purpose |
|------|---------|
| `bot/utils/db.py` | Reusable DB session context manager with retry logic |
| `bot/utils/__init__.py` | Utils package init |
