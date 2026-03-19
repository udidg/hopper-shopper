/* ── GroceryItemRow – Single item with scratch, edit & drag ───── */

import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useListStore } from "@/stores/useListStore";
import { ItemDetailModal } from "./ItemDetailModal";
import type { GroceryItem } from "@/types";

interface Props {
  item: GroceryItem;
}

export function GroceryItemRow({ item }: Props) {
  const { scratchItem } = useListStore();
  const [showModal, setShowModal] = useState(false);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: `item-${item.id}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
    zIndex: isDragging ? 50 : undefined,
  };

  const handleScratch = () => {
    scratchItem(item.id, !item.is_scratched);
  };

  const metaParts: string[] = [];
  if (item.description) metaParts.push(item.description);
  if (item.preferred_store) metaParts.push(`🏪 ${item.preferred_store}`);
  if (item.last_observed_price != null)
    metaParts.push(`💰 ₪${item.last_observed_price.toFixed(2)}`);

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        className={`grocery-item ${item.is_scratched ? "scratched" : ""}`}
      >
        <div
          className={`item-checkbox ${item.is_scratched ? "checked" : ""}`}
          onClick={handleScratch}
        >
          {item.is_scratched && "✓"}
        </div>

        <div className="item-content" onClick={handleScratch}>
          <div className="item-name">{item.name}</div>
          {metaParts.length > 0 && (
            <div className="item-meta">
              {metaParts.map((part, i) => (
                <span key={i}>{part}</span>
              ))}
            </div>
          )}
        </div>

        <div className="item-actions">
          <button className="edit-btn" onClick={() => setShowModal(true)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="5" r="1.5" />
              <circle cx="12" cy="12" r="1.5" />
              <circle cx="12" cy="19" r="1.5" />
            </svg>
          </button>
          <span
            className="item-drag-handle"
            {...attributes}
            {...listeners}
          >
            ⠿
          </span>
        </div>
      </div>

      {showModal && (
        <ItemDetailModal item={item} onClose={() => setShowModal(false)} />
      )}
    </>
  );
}
