/* ── GroceryList – Main view with multi-container drag & drop ── */

import { useMemo, useState, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  TouchSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragOverEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import { arrayMove } from "@dnd-kit/sortable";
import { useListStore } from "@/stores/useListStore";
import { SectionGroup } from "./SectionGroup";
import type { GroceryItem } from "@/types";

/** Extract the numeric item ID from a sortable id like "item-42" */
function parseItemId(id: string | number): number | null {
  const str = String(id);
  if (str.startsWith("item-")) {
    return parseInt(str.slice(5), 10);
  }
  return null;
}

/** Extract the category name from a droppable id like "section-Dairy" */
function parseSectionCategory(id: string | number): string | null {
  const str = String(id);
  if (str.startsWith("section-")) {
    return str.slice(8);
  }
  return null;
}

/** Find which category section an item belongs to */
function findContainerCategory(
  itemId: string | number,
  sections: { category: string; items: GroceryItem[] }[]
): string | null {
  const numId = parseItemId(itemId);
  if (numId == null) return null;
  for (const section of sections) {
    if (section.items.some((i) => i.id === numId)) {
      return section.category;
    }
  }
  return null;
}

export function GroceryList() {
  const { items, isLoading, reorderItems, moveItemToCategory } =
    useListStore();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 200, tolerance: 5 },
    })
  );

  const [activeItem, setActiveItem] = useState<GroceryItem | null>(null);

  // Group items by category
  const grouped = useMemo(() => {
    const groups: Record<string, GroceryItem[]> = {};
    const uncategorized: GroceryItem[] = [];

    for (const item of items) {
      if (item.category) {
        if (!groups[item.category]) groups[item.category] = [];
        groups[item.category].push(item);
      } else {
        uncategorized.push(item);
      }
    }

    // Sort: active items first, scratched at bottom within each group
    const sortGroup = (arr: GroceryItem[]) =>
      [...arr].sort((a, b) => {
        if (a.is_scratched !== b.is_scratched) return a.is_scratched ? 1 : -1;
        return a.sort_order - b.sort_order;
      });

    const sections = Object.entries(groups)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, categoryItems]) => ({
        category,
        items: sortGroup(categoryItems),
      }));

    if (uncategorized.length > 0) {
      sections.push({
        category: "Other",
        items: sortGroup(uncategorized),
      });
    }

    return sections;
  }, [items]);

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const { active } = event;
      const numId = parseItemId(active.id);
      if (numId != null) {
        const item = items.find((i) => i.id === numId);
        setActiveItem(item ?? null);
      }
    },
    [items]
  );

  const handleDragOver = useCallback(
    (_event: DragOverEvent) => {
      // Visual feedback is handled by the isOver state in SectionGroup
      // Actual move happens on DragEnd
    },
    []
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveItem(null);

      if (!over) return;

      const activeNumId = parseItemId(active.id);
      if (activeNumId == null) return;

      // Determine the target category
      let targetCategory: string | null = null;

      // Check if dropped on a section
      const sectionCat = parseSectionCategory(over.id);
      if (sectionCat != null) {
        targetCategory = sectionCat;
      } else {
        // Dropped on another item — find that item's category
        targetCategory = findContainerCategory(over.id, grouped);
      }

      // Find the source category
      const sourceCategory = findContainerCategory(active.id, grouped);

      if (targetCategory == null || sourceCategory == null) return;

      if (sourceCategory !== targetCategory) {
        // Cross-category move
        const newCat = targetCategory === "Other" ? null : targetCategory;
        moveItemToCategory(activeNumId, newCat);
      } else {
        // Same category reorder
        const section = grouped.find((s) => s.category === sourceCategory);
        if (!section) return;

        const activeIdx = section.items.findIndex(
          (i) => i.id === activeNumId
        );
        const overNumId = parseItemId(over.id);
        const overIdx =
          overNumId != null
            ? section.items.findIndex((i) => i.id === overNumId)
            : -1;

        if (activeIdx !== -1 && overIdx !== -1 && activeIdx !== overIdx) {
          const reordered = arrayMove(section.items, activeIdx, overIdx);
          // Build full item order: replace this section's items in the global order
          const allItemIds = grouped.flatMap((s) => {
            if (s.category === sourceCategory) {
              return reordered.map((i) => i.id);
            }
            return s.items.map((i) => i.id);
          });
          reorderItems(allItemIds);
        }
      }
    },
    [grouped, moveItemToCategory, reorderItems]
  );

  if (isLoading && items.length === 0) {
    return (
      <div className="empty-state">
        <div className="emoji">⏳</div>
        <p>Loading your list...</p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="empty-state">
        <div className="emoji">🛒</div>
        <p>
          Your list is empty!
          <br />
          Add items using the input below.
        </p>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      {grouped.map((section) => (
        <SectionGroup
          key={section.category}
          category={section.category}
          items={section.items}
        />
      ))}

      <DragOverlay dropAnimation={null}>
        {activeItem ? (
          <div className="grocery-item drag-overlay-item">
            <div className="item-content">
              <div className="item-name">{activeItem.name}</div>
            </div>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
