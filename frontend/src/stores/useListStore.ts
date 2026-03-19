/* ── List & Items Store (Zustand) ────────────────────────────── */

import { create } from "zustand";
import type { GroceryItem, GroceryList, ListDetail } from "@/types";
import * as api from "@/services/api";

interface ListState {
  /* ── State ──────────────────────────────────────────────────── */
  lists: GroceryList[];
  activeListId: number | null;
  activeListDetail: ListDetail | null;
  items: GroceryItem[];
  isLoading: boolean;
  error: string | null;

  /* ── List actions ───────────────────────────────────────────── */
  fetchLists: () => Promise<void>;
  createList: (name: string) => Promise<GroceryList>;
  setActiveList: (listId: number) => void;
  fetchListDetail: (listId: number) => Promise<ListDetail>;
  joinList: (code: string) => Promise<void>;

  /* ── Item actions ───────────────────────────────────────────── */
  fetchItems: (listId: number) => Promise<void>;
  addItem: (payload: {
    name: string;
    category?: string | null;
    description?: string | null;
    preferred_store?: string | null;
    last_observed_price?: number | null;
  }) => Promise<void>;
  scratchItem: (itemId: number, scratched: boolean) => Promise<void>;
  updateItem: (
    itemId: number,
    payload: Partial<GroceryItem>
  ) => Promise<void>;
  deleteItem: (itemId: number) => Promise<void>;
  reorderItems: (itemIds: number[]) => Promise<void>;
  moveItemToCategory: (
    itemId: number,
    newCategory: string | null
  ) => Promise<void>;
  archiveBoughtItems: () => Promise<void>;

  /* ── WebSocket-driven updates ───────────────────────────────── */
  wsAddItem: (item: GroceryItem) => void;
  wsScratchItem: (itemId: number, scratched: boolean) => void;
  wsUpdateItem: (item: Partial<GroceryItem> & { id: number }) => void;
  wsDeleteItem: (itemId: number) => void;
  wsReorderItems: (itemIds: number[]) => void;
}

export const useListStore = create<ListState>((set, get) => ({
  lists: [],
  activeListId: null,
  activeListDetail: null,
  items: [],
  isLoading: false,
  error: null,

  /* ── List actions ───────────────────────────────────────────── */

  fetchLists: async () => {
    set({ isLoading: true });
    try {
      const lists = await api.getMyLists();
      set({ lists, isLoading: false });
    } catch {
      set({ error: "Failed to fetch lists", isLoading: false });
    }
  },

  createList: async (name: string) => {
    const list = await api.createList(name);
    set((s) => ({ lists: [list, ...s.lists] }));
    return list;
  },

  setActiveList: (listId: number) => {
    set({ activeListId: listId, activeListDetail: null, items: [] });
    get().fetchItems(listId);
    get().fetchListDetail(listId);
  },

  fetchListDetail: async (listId: number) => {
    try {
      const detail = await api.getList(listId);
      set({ activeListDetail: detail });
      return detail;
    } catch {
      set({ error: "Failed to fetch list details" });
      throw new Error("Failed to fetch list details");
    }
  },

  joinList: async (code: string) => {
    const list = await api.joinList(code);
    set((s) => ({ lists: [list, ...s.lists] }));
  },

  /* ── Item actions ───────────────────────────────────────────── */

  fetchItems: async (listId: number) => {
    set({ isLoading: true });
    try {
      const items = await api.getItems(listId);
      set({ items, isLoading: false });
    } catch {
      set({ error: "Failed to fetch items", isLoading: false });
    }
  },

  addItem: async (payload) => {
    const listId = get().activeListId;
    if (!listId) return;
    const item = await api.addItem(listId, payload);
    set((s) => ({ items: [...s.items, item] }));
  },

  scratchItem: async (itemId: number, scratched: boolean) => {
    // Optimistic update
    set((s) => ({
      items: s.items.map((i) =>
        i.id === itemId ? { ...i, is_scratched: scratched } : i
      ),
    }));
    try {
      await api.updateItem(itemId, { is_scratched: scratched });
    } catch {
      // Revert on failure
      set((s) => ({
        items: s.items.map((i) =>
          i.id === itemId ? { ...i, is_scratched: !scratched } : i
        ),
      }));
    }
  },

  updateItem: async (itemId: number, payload: Partial<GroceryItem>) => {
    const updated = await api.updateItem(itemId, payload);
    set((s) => ({
      items: s.items.map((i) => (i.id === itemId ? updated : i)),
    }));
  },

  deleteItem: async (itemId: number) => {
    set((s) => ({ items: s.items.filter((i) => i.id !== itemId) }));
    await api.deleteItem(itemId);
  },

  reorderItems: async (itemIds: number[]) => {
    // Optimistic reorder
    const reordered = itemIds
      .map((id, idx) => {
        const item = get().items.find((i) => i.id === id);
        return item ? { ...item, sort_order: idx } : null;
      })
      .filter(Boolean) as GroceryItem[];
    set({ items: reordered });
    await api.sortItems(itemIds);
  },

  moveItemToCategory: async (
    itemId: number,
    newCategory: string | null
  ) => {
    // Optimistic update
    set((s) => ({
      items: s.items.map((i) =>
        i.id === itemId ? { ...i, category: newCategory } : i
      ),
    }));
    try {
      await api.updateItem(itemId, { category: newCategory });
    } catch {
      // Revert on failure — refetch
      const listId = get().activeListId;
      if (listId) get().fetchItems(listId);
    }
  },

  archiveBoughtItems: async () => {
    const listId = get().activeListId;
    if (!listId) return;
    // Optimistic: remove scratched items from UI
    const scratched = get().items.filter((i) => i.is_scratched);
    set((s) => ({ items: s.items.filter((i) => !i.is_scratched) }));
    try {
      await api.archiveScratchedItems(listId);
    } catch {
      // Revert on failure — re-add scratched items
      set((s) => ({ items: [...s.items, ...scratched] }));
    }
  },

  /* ── WebSocket-driven updates ───────────────────────────────── */

  wsAddItem: (item: GroceryItem) => {
    set((s) => {
      // Avoid duplicates
      if (s.items.some((i) => i.id === item.id)) return s;
      return { items: [...s.items, item] };
    });
  },

  wsScratchItem: (itemId: number, scratched: boolean) => {
    set((s) => ({
      items: s.items.map((i) =>
        i.id === itemId ? { ...i, is_scratched: scratched } : i
      ),
    }));
  },

  wsUpdateItem: (item: Partial<GroceryItem> & { id: number }) => {
    set((s) => ({
      items: s.items.map((i) =>
        i.id === item.id ? { ...i, ...item } : i
      ),
    }));
  },

  wsDeleteItem: (itemId: number) => {
    set((s) => ({ items: s.items.filter((i) => i.id !== itemId) }));
  },

  wsReorderItems: (itemIds: number[]) => {
    set((s) => {
      const reordered = itemIds
        .map((id, idx) => {
          const item = s.items.find((i) => i.id === id);
          return item ? { ...item, sort_order: idx } : null;
        })
        .filter(Boolean) as GroceryItem[];
      return { items: reordered };
    });
  },
}));
