# Role & Objective
Act as a Senior Full-Stack Engineer. Your objective is to build a complete Telegram Mini App for a collaborative grocery list. The application will be deployed locally on a NAS using Docker.

## Core Features
The application must support the following core capabilities:
1.  **Collaboration:** Real-time collaboration on grocery lists with other users.
2.  **Rich Item Details:** Add labels, descriptions, and 'additional info' (e.g., "buy the green laundry softener").
3.  **Smart Grouping:** Automatically group the list by store sections/categories.
4.  **Intelligent Suggestions:** Automatically pop up items as suggestions when typing a new item to create a unified repeating items list (e.g., typing 'paper' suggests 'paper towels - Kirkland' based on past entries).
5.  **Item Management:** Scratch an item from the list to mark it as completed.
6.  **Custom Sorting:** Manually change the sorting of a section and remember that choice for future use.
7.  **Store Preferences:** Add a preferred store for specific items.
8.  **Price Tracking:** Add and track the last observed price for items.

---

## Technology Stack

### Backend
*   **Framework:** Python with FastAPI.
*   **Database Migrations:** Alembic for managing schema changes.
*   **Real-time/Collaboration:** WebSockets (FastAPI built-in) for live updates between collaborating users. (Optional: Redis for pub/sub if scaling beyond a single worker).

### Frontend
*   **Framework:** React (bootstrapped with Vite), utilizing the Telegram Web App script for UI integration and theme variables.
*   **State Management:** Zustand or Redux Toolkit for managing complex WebSocket state and optimistic UI updates.
*   **Offline Support:** PWA capabilities (Service Worker) and local caching (e.g., IndexedDB via Dexie.js) for offline viewing and interaction.

### Database
*   **System:** PostgreSQL (via async asyncpg/SQLAlchemy).

### Infrastructure
*   **Containerization:** Docker and Docker Compose.
*   **Reverse Proxy:** Nginx or Traefik for SSL termination (required for Telegram Mini Apps) and routing.

---

## 1. Database Schema Requirements
Please implement the following entities and their relationships using SQLAlchemy:

*   **Users:** `Telegram user_id`, `username`, `display name`.
*   **Lists (Households):** `list_id`, `name`, `created_at`.
*   **ListMembers:** Join table between Users and Lists (for collaboration).
*   **ItemDictionary (The Global/Personal Registry):** Stores historical items for auto-suggestion.
    *   **Fields:** `id`, `user_id` (or `list_id`), `name` (e.g., "Paper Towels - Kirkland"), `default_category`, `last_observed_price`, `preferred_store`.
*   **GroceryItems (The Active List):**
    *   **Fields:** `id`, `list_id`, `name`, `label/category` (Store Section), `description/additional_info` (e.g., "buy the green one"), `is_scratched` (boolean), `sort_order` (integer for manual sorting).

---

## 2. Core Backend Logic & API Endpoints
Implement RESTful endpoints and WebSocket handlers for the following features:

*   **Authentication:** Validate the Telegram Web App `initData` hash to authenticate the user and return a JWT or session token.
*   **List Management:** Create a list, invite a user via a unique link/code, and fetch the active list.
*   **Real-Time Collaboration (WebSocket):** When User A adds/scratches an item, broadcast the state change to all active WebSocket connections for that `list_id`.
*   **Auto-Suggestion Engine (Endpoint: `GET /suggestions?q={query}`):** Query the `ItemDictionary` for partial string matches to return previous items, their categories, last prices, and preferred stores.
*   **Auto-Grouping Logic:** When an item is added, automatically assign its label/category based on the `ItemDictionary` default or a predefined map (e.g., Produce, Dairy, Cleaning).
*   **Manual Sorting (Endpoint: `PUT /items/sort`):** Accept an array of item IDs in their new order and update the `sort_order` integers in the database.

---

## 3. Frontend UI/UX Requirements (React)
The UI should feel native to Telegram, utilizing Telegram's CSS variables (`var(--tg-theme-bg-color)`, etc.) for seamless light/dark mode switching.

*   **Main View:** A list grouped by "Store Section" (Category). Group headers should be sticky.
*   **Input Bar:** A fixed bottom input field. As the user types, a floating suggestion menu should appear above the input, pulling from the `/suggestions` endpoint. Selecting a suggestion populates the item, category, price, and store.
*   **Item Component:**
    *   Checkbox or tap-to-strike functionality (scratching an item). Scratched items should move to the bottom of their group or a dedicated "Completed" section.
    *   Sub-text displaying `description/additional_info`, `preferred_store`, and `last_observed_price`.
*   **Drag-and-Drop:** Implement drag-and-drop functionality (using a library like `dnd-kit`) to allow manual reordering of store sections, persisting the choice to the backend.
*   **Item Details Modal:** Tapping an "edit" icon on an item opens a drawer to edit the description, change the label, update the price, or change the store.
*   **Offline Sync:** Queue actions (like scratching an item) locally when offline and sync with the backend upon reconnection.

---

## 4. Infrastructure & Deployment
Create a `docker-compose.yml` and corresponding Dockerfiles:

*   **Reverse Proxy:** Nginx or Traefik container configured for SSL termination and routing traffic to the frontend and backend.
*   **Backend Service:** Python 3.11+ running Uvicorn.
*   **Frontend Service:** Node container serving the React build (or an Nginx container serving static files).
*   **Database Service:** PostgreSQL container with a persistent volume mapped for local NAS storage.
*   **(Optional) Redis Service:** For WebSocket pub/sub if needed.

Include a `.env.example` file detailing required environment variables (Telegram Bot Token, DB credentials, CORS origins, SSL cert paths).

---

## Execution Plan
Please acknowledge these requirements and begin by outputting the `docker-compose.yml` and the SQLAlchemy database models first.