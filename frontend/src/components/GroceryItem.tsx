/* ── GroceryItemRow – Single item with scratch & edit ─────────── */

import { useState } from "react";
import { useListStore } from "@/stores/useListStore";
import { ItemDetailModal } from "./ItemDetailModal";
import type { GroceryItem } from "@/types";

interface Props {
  item: GroceryItem;
}

export function GroceryItemRow({ item }: Props) {
  const { scratchItem } = useListStore();
  const [showModal, setShowModal] = useState(false);

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
      <div className={`grocery-item ${item.is_scratched ? "scratched" : ""}`}>
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
            ✏️
          </button>
        </div>
      </div>

      {showModal && (
        <ItemDetailModal item={item} onClose={() => setShowModal(false)} />
      )}
    </>
  );
}
