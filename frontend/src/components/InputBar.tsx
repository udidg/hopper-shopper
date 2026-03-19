/* ── InputBar – Bottom input with floating suggestions ────────── */

import { useState, useEffect, useRef } from "react";
import { useListStore } from "@/stores/useListStore";
import { useSuggestions } from "@/hooks/useSuggestions";
import { getCategorySuggestion } from "@/services/api";
import { SuggestionMenu } from "./SuggestionMenu";
import type { Suggestion } from "@/types";

export function InputBar() {
  const { addItem } = useListStore();
  const { query, setQuery, suggestions, clear } = useSuggestions();
  const [selectedSuggestion, setSelectedSuggestion] =
    useState<Suggestion | null>(null);
  const [suggestedCategory, setSuggestedCategory] = useState<string | null>(
    null
  );
  const categoryDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );

  // Debounced category suggestion when no suggestion is selected
  useEffect(() => {
    // Clear any pending debounce
    if (categoryDebounceRef.current) {
      clearTimeout(categoryDebounceRef.current);
      categoryDebounceRef.current = null;
    }

    const trimmed = query.trim();

    // Only fetch category if:
    // - query is at least 2 chars
    // - no suggestion is selected (user typed freely)
    // - no exact match in suggestions
    if (
      trimmed.length >= 2 &&
      !selectedSuggestion &&
      !suggestions.some(
        (s) => s.name.toLowerCase() === trimmed.toLowerCase()
      )
    ) {
      categoryDebounceRef.current = setTimeout(async () => {
        try {
          const cat = await getCategorySuggestion(trimmed);
          setSuggestedCategory(cat);
        } catch {
          setSuggestedCategory(null);
        }
      }, 500);
    } else {
      setSuggestedCategory(null);
    }

    return () => {
      if (categoryDebounceRef.current) {
        clearTimeout(categoryDebounceRef.current);
      }
    };
  }, [query, selectedSuggestion, suggestions]);

  const handleSubmit = async () => {
    const name = query.trim();
    if (!name) return;

    await addItem({
      name,
      category:
        selectedSuggestion?.default_category ?? suggestedCategory ?? undefined,
      preferred_store: selectedSuggestion?.preferred_store ?? undefined,
      last_observed_price:
        selectedSuggestion?.last_observed_price ?? undefined,
    });

    clear();
    setSelectedSuggestion(null);
    setSuggestedCategory(null);
  };

  const handleSelectSuggestion = (suggestion: Suggestion) => {
    setQuery(suggestion.name);
    setSelectedSuggestion(suggestion);
    setSuggestedCategory(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <>
      {suggestions.length > 0 && (
        <SuggestionMenu
          suggestions={suggestions}
          onSelect={handleSelectSuggestion}
        />
      )}
      {suggestedCategory && !selectedSuggestion && (
        <div className="category-chip-bar">
          <span className="category-chip">
            📂 {suggestedCategory}
          </span>
          <button
            className="category-chip-dismiss"
            onClick={() => setSuggestedCategory(null)}
          >
            ✕
          </button>
        </div>
      )}
      <div className="input-bar">
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedSuggestion(null);
          }}
          onKeyDown={handleKeyDown}
          placeholder="Add an item..."
          autoComplete="off"
        />
        <button className="send-btn" onClick={handleSubmit}>
          +
        </button>
      </div>
    </>
  );
}
