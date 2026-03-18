/* ── useOfflineSync – Queue actions offline, sync on reconnect ── */

import { useCallback, useEffect } from "react";
import {
  getPendingActions,
  markActionSynced,
  clearSyncedActions,
  queueOfflineAction,
} from "@/services/offlineDb";
import * as api from "@/services/api";

export function useOfflineSync() {
  const isOnline = typeof navigator !== "undefined" ? navigator.onLine : true;

  const syncPendingActions = useCallback(async () => {
    const pending = await getPendingActions();

    for (const action of pending) {
      try {
        switch (action.action) {
          case "scratch_item":
            await api.updateItem(
              action.payload.item_id as number,
              { is_scratched: action.payload.is_scratched as boolean }
            );
            break;
          case "add_item":
            await api.addItem(
              action.payload.list_id as number,
              action.payload as { name: string }
            );
            break;
          case "delete_item":
            await api.deleteItem(action.payload.item_id as number);
            break;
        }
        if (action.id) {
          await markActionSynced(action.id);
        }
      } catch {
        // Stop syncing on first failure (likely still offline)
        break;
      }
    }

    await clearSyncedActions();
  }, []);

  // Sync when coming back online
  useEffect(() => {
    const handleOnline = () => {
      syncPendingActions();
    };

    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, [syncPendingActions]);

  // Try syncing on mount
  useEffect(() => {
    if (isOnline) {
      syncPendingActions();
    }
  }, [isOnline, syncPendingActions]);

  return { isOnline, queueOfflineAction, syncPendingActions };
}
