/* ── SectionGroup – Droppable category container with sortable items ── */

import { useDroppable } from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { GroceryItemRow } from "./GroceryItem";
import type { GroceryItem } from "@/types";

interface Props {
  category: string;
  items: GroceryItem[];
}

export function SectionGroup({ category, items }: Props) {
  const { setNodeRef, isOver } = useDroppable({
    id: `section-${category}`,
    data: { type: "section", category },
  });

  const itemIds = items.map((item) => `item-${item.id}`);

  return (
    <div
      ref={setNodeRef}
      className={`section-group ${isOver ? "section-drop-target" : ""}`}
    >
      <div className="section-header">
        <span>{category}</span>
      </div>
      <SortableContext items={itemIds} strategy={verticalListSortingStrategy}>
        {items.map((item) => (
          <GroceryItemRow key={item.id} item={item} />
        ))}
      </SortableContext>
      {items.length === 0 && (
        <div className="section-empty-drop">Drop items here</div>
      )}
    </div>
  );
}
