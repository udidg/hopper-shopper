"""WebSocket message handlers for real-time grocery list collaboration."""

import json
import logging

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.grocery_item import GroceryItem
from app.models.list_member import ListMember
from app.services.auth import decode_access_token
from app.services.grouping import guess_category_smart
from app.services.suggestion import upsert_dictionary_entry
from app.websocket.manager import manager

logger = logging.getLogger(__name__)


async def _authenticate_ws(websocket: WebSocket) -> int | None:
    """
    Authenticate a WebSocket connection via token query param.

    Returns user_id if valid, None otherwise.
    """
    token = websocket.query_params.get("token")
    if not token:
        return None
    payload = decode_access_token(token)
    if payload is None:
        return None
    return int(payload["sub"])


async def _check_ws_membership(
    user_id: int, list_id: int, db: AsyncSession
) -> bool:
    """Check if user is a member of the list."""
    result = await db.execute(
        select(ListMember).where(
            ListMember.user_id == user_id,
            ListMember.list_id == list_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def websocket_endpoint(websocket: WebSocket, list_id: int):
    """
    WebSocket endpoint for real-time list collaboration.

    Protocol:
    - Connect with ?token=<jwt> query parameter
    - Send JSON messages with "action" field
    - Receive broadcast JSON messages from other users

    Actions:
    - add_item: {action: "add_item", name, category?, description?, preferred_store?, last_observed_price?}
    - scratch_item: {action: "scratch_item", item_id, is_scratched}
    - update_item: {action: "update_item", item_id, ...fields}
    - delete_item: {action: "delete_item", item_id}
    - reorder: {action: "reorder", item_ids: [...]}
    """
    # Authenticate
    user_id = await _authenticate_ws(websocket)
    if user_id is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # Check membership
    async with async_session() as db:
        is_member = await _check_ws_membership(user_id, list_id, db)
    if not is_member:
        await websocket.close(code=4003, reason="Not a member of this list")
        return

    # Connect
    await manager.connect(websocket, list_id)
    logger.info(
        f"User {user_id} connected to list {list_id} "
        f"({manager.get_connection_count(list_id)} connections)"
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket, {"error": "Invalid JSON"}
                )
                continue

            action = data.get("action")
            if not action:
                await manager.send_personal(
                    websocket, {"error": "Missing 'action' field"}
                )
                continue

            # Process action within a database session
            async with async_session() as db:
                try:
                    result = await _handle_action(
                        action, data, user_id, list_id, db
                    )
                    await db.commit()

                    if result:
                        # Send confirmation to sender
                        await manager.send_personal(
                            websocket,
                            {"type": "ack", "action": action, **result},
                        )
                        # Broadcast to other users
                        await manager.broadcast(
                            list_id,
                            {"type": "update", "action": action, "user_id": user_id, **result},
                            exclude=websocket,
                        )
                except Exception as e:
                    await db.rollback()
                    logger.error(f"WS action error: {e}")
                    await manager.send_personal(
                        websocket, {"error": str(e)}
                    )

    except WebSocketDisconnect:
        manager.disconnect(websocket, list_id)
        logger.info(
            f"User {user_id} disconnected from list {list_id} "
            f"({manager.get_connection_count(list_id)} connections)"
        )


async def _handle_action(
    action: str,
    data: dict,
    user_id: int,
    list_id: int,
    db: AsyncSession,
) -> dict | None:
    """Route an action to its handler and return the result payload."""

    if action == "add_item":
        return await _handle_add_item(data, user_id, list_id, db)
    elif action == "scratch_item":
        return await _handle_scratch_item(data, user_id, list_id, db)
    elif action == "update_item":
        return await _handle_update_item(data, user_id, list_id, db)
    elif action == "delete_item":
        return await _handle_delete_item(data, user_id, list_id, db)
    elif action == "reorder":
        return await _handle_reorder(data, user_id, list_id, db)
    else:
        return {"error": f"Unknown action: {action}"}


async def _handle_add_item(
    data: dict, user_id: int, list_id: int, db: AsyncSession
) -> dict:
    """Handle adding a new item via WebSocket."""
    from sqlalchemy import func

    name = data.get("name")
    if not name:
        return {"error": "Missing 'name'"}

    category = data.get("category") or await guess_category_smart(name)

    # Get next sort order
    max_order = await db.execute(
        select(func.coalesce(func.max(GroceryItem.sort_order), 0)).where(
            GroceryItem.list_id == list_id
        )
    )
    next_order = max_order.scalar() + 1

    item = GroceryItem(
        list_id=list_id,
        name=name,
        category=category,
        description=data.get("description"),
        preferred_store=data.get("preferred_store"),
        last_observed_price=data.get("last_observed_price"),
        sort_order=next_order,
        added_by=user_id,
    )
    db.add(item)
    await db.flush()

    # Upsert dictionary
    await upsert_dictionary_entry(
        db=db,
        user_id=user_id,
        name=name,
        category=category,
        price=data.get("last_observed_price"),
        store=data.get("preferred_store"),
        list_id=list_id,
    )

    return {
        "item": {
            "id": item.id,
            "list_id": item.list_id,
            "name": item.name,
            "category": item.category,
            "description": item.description,
            "is_scratched": item.is_scratched,
            "sort_order": item.sort_order,
            "preferred_store": item.preferred_store,
            "last_observed_price": float(item.last_observed_price) if item.last_observed_price else None,
            "added_by": item.added_by,
        }
    }


async def _handle_scratch_item(
    data: dict, user_id: int, list_id: int, db: AsyncSession
) -> dict:
    """Handle scratching/un-scratching an item."""
    item_id = data.get("item_id")
    is_scratched = data.get("is_scratched", True)

    result = await db.execute(
        select(GroceryItem).where(
            GroceryItem.id == item_id, GroceryItem.list_id == list_id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return {"error": "Item not found"}

    item.is_scratched = is_scratched
    return {"item_id": item.id, "is_scratched": item.is_scratched}


async def _handle_update_item(
    data: dict, user_id: int, list_id: int, db: AsyncSession
) -> dict:
    """Handle updating item fields."""
    item_id = data.get("item_id")

    result = await db.execute(
        select(GroceryItem).where(
            GroceryItem.id == item_id, GroceryItem.list_id == list_id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return {"error": "Item not found"}

    updatable = ["name", "category", "description", "preferred_store", "last_observed_price"]
    for field in updatable:
        if field in data:
            setattr(item, field, data[field])

    return {
        "item": {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "description": item.description,
            "is_scratched": item.is_scratched,
            "preferred_store": item.preferred_store,
            "last_observed_price": float(item.last_observed_price) if item.last_observed_price else None,
        }
    }


async def _handle_delete_item(
    data: dict, user_id: int, list_id: int, db: AsyncSession
) -> dict:
    """Handle deleting an item."""
    item_id = data.get("item_id")

    result = await db.execute(
        select(GroceryItem).where(
            GroceryItem.id == item_id, GroceryItem.list_id == list_id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        return {"error": "Item not found"}

    await db.delete(item)
    return {"item_id": item_id}


async def _handle_reorder(
    data: dict, user_id: int, list_id: int, db: AsyncSession
) -> dict:
    """Handle reordering items."""
    item_ids = data.get("item_ids", [])

    for index, item_id in enumerate(item_ids):
        result = await db.execute(
            select(GroceryItem).where(
                GroceryItem.id == item_id, GroceryItem.list_id == list_id
            )
        )
        item = result.scalar_one_or_none()
        if item:
            item.sort_order = index

    return {"item_ids": item_ids}
