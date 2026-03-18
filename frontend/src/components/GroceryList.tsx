/* ── GroceryList – Main view grouped by category ─────────────── */

import { useMemo } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useListStore } from "@/stores/useListStore";
import { SectionGroup } from "./SectionGroup";
import type { GroceryItem } from "@/types";

export function GroceryList() {
  const { items, isLoading, reorderItems } = useListStore();

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

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

  const sectionIds = grouped.map((s) => s.category);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    // Reorder sections
    const oldIndex = sectionIds.indexOf(active.id as string);
    const newIndex = sectionIds.indexOf(over.id as string);

    if (oldIndex === -1 || newIndex === -1) return;

    // Build new item order based on reordered sections
    const reorderedSections = [...grouped];
    const [moved] = reorderedSections.splice(oldIndex, 1);
    reorderedSections.splice(newIndex, 0, moved);

    const newItemIds = reorderedSections.flatMap((s) =>
      s.items.map((i) => i.id)
    );
    reorderItems(newItemIds);
  };

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
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <SortableContext
        items={sectionIds}
        strategy={verticalListSortingStrategy}
      >
        {grouped.map((section) => (
          <SectionGroup
            key={section.category}
            category={section.category}
            items={section.items}
          />
        ))}
      </SortableContext>
    </DndContext>
  );
}
