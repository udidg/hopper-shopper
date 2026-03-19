/* ── REST API client ─────────────────────────────────────────── */

import axios from "axios";
import type {
  Department,
  GroceryItem,
  GroceryList,
  ItemCreatePayload,
  ItemUpdatePayload,
  ListDetail,
  Suggestion,
  User,
} from "@/types";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
});

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/* ── Auth ─────────────────────────────────────────────────────── */

export async function authenticateTelegram(
  initData: string
): Promise<{ access_token: string; user: User }> {
  const { data } = await api.post("/auth/telegram", { init_data: initData });
  return data;
}

/* ── Lists ────────────────────────────────────────────────────── */

export async function createList(name: string): Promise<GroceryList> {
  const { data } = await api.post("/lists", { name });
  return data;
}

export async function getMyLists(): Promise<GroceryList[]> {
  const { data } = await api.get("/lists");
  return data;
}

export async function getList(listId: number): Promise<ListDetail> {
  const { data } = await api.get(`/lists/${listId}`);
  return data;
}

export async function joinList(inviteCode: string): Promise<GroceryList> {
  const { data } = await api.post("/lists/join", { invite_code: inviteCode });
  return data;
}

/* ── Items ────────────────────────────────────────────────────── */

export async function getItems(listId: number): Promise<GroceryItem[]> {
  const { data } = await api.get(`/lists/${listId}/items`);
  return data;
}

export async function addItem(
  listId: number,
  payload: ItemCreatePayload
): Promise<GroceryItem> {
  const { data } = await api.post(`/lists/${listId}/items`, payload);
  return data;
}

export async function updateItem(
  itemId: number,
  payload: ItemUpdatePayload
): Promise<GroceryItem> {
  const { data } = await api.patch(`/items/${itemId}`, payload);
  return data;
}

export async function deleteItem(itemId: number): Promise<void> {
  await api.delete(`/items/${itemId}`);
}

export async function sortItems(itemIds: number[]): Promise<void> {
  await api.put("/items/sort", { item_ids: itemIds });
}

export async function archiveScratchedItems(
  listId: number
): Promise<{ archived_count: number }> {
  const { data } = await api.delete(`/lists/${listId}/items/scratched`);
  return data;
}

/* ── Suggestions ──────────────────────────────────────────────── */

export async function getSuggestions(query: string): Promise<Suggestion[]> {
  const { data } = await api.get("/suggestions", { params: { q: query } });
  return data;
}

/* ── Category Suggestion ─────────────────────────────────────── */

export async function getCategorySuggestion(
  itemName: string
): Promise<string | null> {
  const { data } = await api.get("/suggestions/category", {
    params: { item_name: itemName },
  });
  return data.category ?? null;
}

/* ── Departments ──────────────────────────────────────────────── */

export async function getDepartments(query: string = ""): Promise<Department[]> {
  const { data } = await api.get("/suggestions/departments", {
    params: { q: query },
  });
  return data;
}

export default api;
