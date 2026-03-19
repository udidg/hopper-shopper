/* ── GroceryList – Main view with grouped items ──────────────── */

import { useMemo } from "react";
import { useListStore } from "@/stores/useListStore";
import { SectionGroup } from "./SectionGroup";
import type { GroceryItem } from "@/types";

export function GroceryList() {
  const { items, isLoading } = useListStore();

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
    <div className="grocery-list-content">
      {grouped.map((section) => (
        <SectionGroup
          key={section.category}
          category={section.category}
          items={section.items}
        />
      ))}
    </div>
  );
}
