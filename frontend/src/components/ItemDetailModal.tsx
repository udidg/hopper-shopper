/* ── ItemDetailModal – Edit drawer for item details ───────────── */

import { useState, useRef, useEffect, useMemo } from "react";
import { useListStore } from "@/stores/useListStore";
import { useDepartments } from "@/hooks/useDepartments";
import type { GroceryItem, Department } from "@/types";

interface Props {
  item: GroceryItem;
  onClose: () => void;
}

export function ItemDetailModal({ item, onClose }: Props) {
  const { items, updateItem, deleteItem, reorderItems } = useListStore();
  const {
    setQuery: setDeptQuery,
    departments,
  } = useDepartments();

  const [name, setName] = useState(item.name);
  const [category, setCategory] = useState(item.category || "");
  const [description, setDescription] = useState(item.description || "");
  const [store, setStore] = useState(item.preferred_store || "");
  const [price, setPrice] = useState(
    item.last_observed_price?.toString() || ""
  );
  const [showDeptDropdown, setShowDeptDropdown] = useState(false);
  const deptInputRef = useRef<HTMLInputElement>(null);

  // Sync category input with department query
  useEffect(() => {
    setDeptQuery(category);
  }, [category, setDeptQuery]);

  // Get all unique categories for move-to-category
  const allCategories = useMemo(() => {
    const cats = new Set<string>();
    for (const i of items) {
      if (i.category) cats.add(i.category);
    }
    return Array.from(cats).sort();
  }, [items]);

  // Get sibling items in same category for reordering
  const siblings = useMemo(() => {
    return items
      .filter((i) => (i.category || "Other") === (item.category || "Other"))
      .sort((a, b) => {
        if (a.is_scratched !== b.is_scratched) return a.is_scratched ? 1 : -1;
        return a.sort_order - b.sort_order;
      });
  }, [items, item.category]);

  const currentIndex = siblings.findIndex((i) => i.id === item.id);
  const canMoveUp = currentIndex > 0;
  const canMoveDown = currentIndex < siblings.length - 1;

  const handleMoveUp = async () => {
    if (!canMoveUp) return;
    const newSiblings = [...siblings];
    [newSiblings[currentIndex - 1], newSiblings[currentIndex]] = [
      newSiblings[currentIndex],
      newSiblings[currentIndex - 1],
    ];
    // Build full reorder: replace this category's items in global order
    const otherItems = items.filter(
      (i) => (i.category || "Other") !== (item.category || "Other")
    );
    const allIds = [...otherItems, ...newSiblings].map((i) => i.id);
    await reorderItems(allIds);
  };

  const handleMoveDown = async () => {
    if (!canMoveDown) return;
    const newSiblings = [...siblings];
    [newSiblings[currentIndex], newSiblings[currentIndex + 1]] = [
      newSiblings[currentIndex + 1],
      newSiblings[currentIndex],
    ];
    const otherItems = items.filter(
      (i) => (i.category || "Other") !== (item.category || "Other")
    );
    const allIds = [...otherItems, ...newSiblings].map((i) => i.id);
    await reorderItems(allIds);
  };

  const handleSelectDepartment = (dept: Department) => {
    const selectedName = dept.name_he || dept.name || "";
    setCategory(selectedName);
    setShowDeptDropdown(false);
  };

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

        <div className="form-group dept-autocomplete">
          <label>Category (Store Section)</label>
          <input
            ref={deptInputRef}
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setShowDeptDropdown(true);
            }}
            onFocus={() => setShowDeptDropdown(true)}
            onBlur={() => {
              setTimeout(() => setShowDeptDropdown(false), 200);
            }}
            placeholder="e.g. Produce, Dairy, ירקות ופירות"
            autoComplete="off"
          />
          {showDeptDropdown && departments.length > 0 && (
            <div className="dept-dropdown">
              {departments.map((dept, idx) => (
                <div
                  key={idx}
                  className="dept-dropdown-item"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleSelectDepartment(dept)}
                >
                  <span className="dept-name-en">{dept.name}</span>
                  {dept.name_he && (
                    <span className="dept-name-he">{dept.name_he}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Quick move to existing category */}
        {allCategories.length > 1 && (
          <div className="form-group">
            <label>Move to Category</label>
            <div className="category-chips">
              {allCategories.map((cat) => (
                <button
                  key={cat}
                  className={`category-move-chip ${
                    cat === (item.category || "Other") ? "active" : ""
                  }`}
                  onClick={() => setCategory(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>
        )}

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

        {/* Reorder controls */}
        <div className="form-group">
          <label>Reorder in Section</label>
          <div className="reorder-controls">
            <button
              className="btn btn-secondary reorder-btn"
              onClick={handleMoveUp}
              disabled={!canMoveUp}
            >
              ↑ Move Up
            </button>
            <button
              className="btn btn-secondary reorder-btn"
              onClick={handleMoveDown}
              disabled={!canMoveDown}
            >
              ↓ Move Down
            </button>
          </div>
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
