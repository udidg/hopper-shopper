/* ── SectionGroup – Category container with items ─────────────── */

import { GroceryItemRow } from "./GroceryItem";
import type { GroceryItem } from "@/types";

interface Props {
  category: string;
  items: GroceryItem[];
}

export function SectionGroup({ category, items }: Props) {
  return (
    <div className="section-group">
      <div className="section-header">
        <span>{category}</span>
        <span className="section-count">{items.length}</span>
      </div>
      {items.map((item) => (
        <GroceryItemRow key={item.id} item={item} />
      ))}
    </div>
  );
}
