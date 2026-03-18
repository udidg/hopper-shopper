/* ── Shared TypeScript types ─────────────────────────────────── */

export interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  display_name: string;
}

export interface GroceryList {
  id: number;
  name: string;
  invite_code: string;
  created_at: string;
}

export interface ListMember {
  id: number;
  user_id: number;
  role: string;
  user: User;
}

export interface ListDetail extends GroceryList {
  members: ListMember[];
}

export interface GroceryItem {
  id: number;
  list_id: number;
  name: string;
  category: string | null;
  description: string | null;
  is_scratched: boolean;
  sort_order: number;
  preferred_store: string | null;
  last_observed_price: number | null;
  added_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface Suggestion {
  id: number;
  name: string;
  default_category: string | null;
  last_observed_price: number | null;
  preferred_store: string | null;
}

export interface ItemCreatePayload {
  name: string;
  category?: string | null;
  description?: string | null;
  preferred_store?: string | null;
  last_observed_price?: number | null;
}

export interface ItemUpdatePayload {
  name?: string;
  category?: string | null;
  description?: string | null;
  is_scratched?: boolean;
  preferred_store?: string | null;
  last_observed_price?: number | null;
}

/* ── WebSocket message types ─────────────────────────────────── */

export type WSAction =
  | "add_item"
  | "scratch_item"
  | "update_item"
  | "delete_item"
  | "reorder";

export interface WSMessage {
  type: "ack" | "update" | "error";
  action: WSAction;
  user_id?: number;
  item?: Partial<GroceryItem>;
  item_id?: number;
  is_scratched?: boolean;
  item_ids?: number[];
  error?: string;
}
