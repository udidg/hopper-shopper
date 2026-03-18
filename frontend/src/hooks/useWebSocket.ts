/* ── useWebSocket – Real-time sync with backend ──────────────── */

import { useCallback, useEffect, useRef } from "react";
import { useAuthStore } from "@/stores/useAuthStore";
import { useListStore } from "@/stores/useListStore";
import type { GroceryItem, WSMessage } from "@/types";

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || "/ws";

export function useWebSocket(listId: number | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { token } = useAuthStore();
  const { wsAddItem, wsScratchItem, wsUpdateItem, wsDeleteItem, wsReorderItems } =
    useListStore();

  const connect = useCallback(() => {
    if (!listId || !token) return;

    // Build WebSocket URL
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}${WS_BASE}/${listId}?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log(`[WS] Connected to list ${listId}`);
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);

        if (msg.type === "error") {
          console.error("[WS] Error:", msg.error);
          return;
        }

        // Only process broadcasts from other users (type === "update")
        if (msg.type !== "update") return;

        switch (msg.action) {
          case "add_item":
            if (msg.item) {
              wsAddItem(msg.item as GroceryItem);
            }
            break;
          case "scratch_item":
            if (msg.item_id != null && msg.is_scratched != null) {
              wsScratchItem(msg.item_id, msg.is_scratched);
            }
            break;
          case "update_item":
            if (msg.item && msg.item.id) {
              wsUpdateItem(msg.item as GroceryItem & { id: number });
            }
            break;
          case "delete_item":
            if (msg.item_id != null) {
              wsDeleteItem(msg.item_id);
            }
            break;
          case "reorder":
            if (msg.item_ids) {
              wsReorderItems(msg.item_ids);
            }
            break;
        }
      } catch (err) {
        console.error("[WS] Failed to parse message:", err);
      }
    };

    ws.onclose = (event) => {
      console.log(`[WS] Disconnected (code: ${event.code})`);
      wsRef.current = null;

      // Auto-reconnect after 3 seconds (unless intentionally closed)
      if (event.code !== 1000 && event.code !== 4001 && event.code !== 4003) {
        reconnectTimer.current = setTimeout(() => {
          console.log("[WS] Reconnecting...");
          connect();
        }, 3000);
      }
    };

    ws.onerror = (err) => {
      console.error("[WS] Error:", err);
    };
  }, [listId, token, wsAddItem, wsScratchItem, wsUpdateItem, wsDeleteItem, wsReorderItems]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.close(1000);
        wsRef.current = null;
      }
    };
  }, [connect]);

  return wsRef;
}
