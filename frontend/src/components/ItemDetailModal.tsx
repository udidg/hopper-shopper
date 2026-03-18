/* ── ItemDetailModal – Edit drawer for item details ───────────── */

import { useState } from "react";
import { useListStore } from "@/stores/useListStore";
import type { GroceryItem } from "@/types";

interface Props {
  item: GroceryItem;
  onClose: () => void;
}

export function ItemDetailModal({ item, onClose }: Props) {
  const { updateItem, deleteItem } = useListStore();

  const [name, setName] = useState(item.name);
  const [category, setCategory] = useState(item.category || "");
  const [description, setDescription] = useState(item.description || "");
  const [store, setStore] = useState(item.preferred_store || "");
  const [price, setPrice] = useState(
    item.last_observed_price?.toString() || ""
  );

  const handleSave = async () => {
    await updateItem(item.id, {
      name,
      category: category || null,
      description: description || null,
      preferred_store: store || null,
      last_observed_price: price ? parseFloat(price) : null,
    });
    onClose();
  };

  const handleDelete = async () => {
    await deleteItem(item.id);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="modal-handle" />
        <h3>Edit Item</h3>

        <div className="form-group">
          <label>Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Item name"
          />
        </div>

        <div className="form-group">
          <label>Category (Store Section)</label>
          <input
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g. Produce, Dairy, Cleaning"
          />
        </div>

        <div className="form-group">
          <label>Additional Info</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="e.g. buy the green one"
          />
        </div>

        <div className="form-group">
          <label>Preferred Store</label>
          <input
            value={store}
            onChange={(e) => setStore(e.target.value)}
            placeholder="e.g. Costco, Rami Levy"
          />
        </div>

        <div className="form-group">
          <label>Last Observed Price</label>
          <input
            type="number"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="0.00"
          />
        </div>

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-danger" onClick={handleDelete}>
            Delete
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
}
