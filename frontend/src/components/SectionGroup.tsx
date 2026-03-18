/* ── SectionGroup – Sticky header + items for a category ─────── */

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GroceryItemRow } from "./GroceryItem";
import type { GroceryItem } from "@/types";

interface Props {
  category: string;
  items: GroceryItem[];
}

export function SectionGroup({ category, items }: Props) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: category });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} className="section-group">
      <div className="section-header" {...attributes} {...listeners}>
        <span>{category}</span>
        <span className="drag-handle">⠿</span>
      </div>
      {items.map((item) => (
        <GroceryItemRow key={item.id} item={item} />
      ))}
    </div>
  );
}
