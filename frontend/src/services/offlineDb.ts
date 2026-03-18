/* ── Dexie.js – IndexedDB for offline caching ────────────────── */

import Dexie, { type Table } from "dexie";

export interface OfflineAction {
  id?: number;
  action: string;
  payload: Record<string, unknown>;
  timestamp: number;
  synced: boolean;
}

export interface CachedItem {
  id: number;
  list_id: number;
  name: string;
  category: string | null;
  description: string | null;
  is_scratched: boolean;
  sort_order: number;
  preferred_store: string | null;
  last_observed_price: number | null;
}

class HopperDatabase extends Dexie {
  offlineActions!: Table<OfflineAction>;
  cachedItems!: Table<CachedItem>;

  constructor() {
    super("HopperShopperDB");
    this.version(1).stores({
      offlineActions: "++id, action, synced, timestamp",
      cachedItems: "id, list_id, name, category",
    });
  }
}

export const db = new HopperDatabase();

/* ── Helper functions ────────────────────────────────────────── */

export async function queueOfflineAction(
  action: string,
  payload: Record<string, unknown>
): Promise<void> {
  await db.offlineActions.add({
    action,
    payload,
    timestamp: Date.now(),
    synced: false,
  });
}

export async function getPendingActions(): Promise<OfflineAction[]> {
  return db.offlineActions.where("synced").equals(0).sortBy("timestamp");
}

export async function markActionSynced(id: number): Promise<void> {
  await db.offlineActions.update(id, { synced: true });
}

export async function clearSyncedActions(): Promise<void> {
  await db.offlineActions.where("synced").equals(1).delete();
}

export async function cacheItems(items: CachedItem[]): Promise<void> {
  await db.cachedItems.bulkPut(items);
}

export async function getCachedItems(listId: number): Promise<CachedItem[]> {
  return db.cachedItems.where("list_id").equals(listId).sortBy("sort_order");
}
