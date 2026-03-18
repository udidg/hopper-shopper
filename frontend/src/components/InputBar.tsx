/* ── InputBar – Bottom input with floating suggestions ────────── */

import { useState } from "react";
import { useListStore } from "@/stores/useListStore";
import { useSuggestions } from "@/hooks/useSuggestions";
import { SuggestionMenu } from "./SuggestionMenu";
import type { Suggestion } from "@/types";

export function InputBar() {
  const { addItem } = useListStore();
  const { query, setQuery, suggestions, clear } = useSuggestions();
  const [selectedSuggestion, setSelectedSuggestion] =
    useState<Suggestion | null>(null);

  const handleSubmit = async () => {
    const name = query.trim();
    if (!name) return;

    await addItem({
      name,
      category: selectedSuggestion?.default_category ?? undefined,
      preferred_store: selectedSuggestion?.preferred_store ?? undefined,
      last_observed_price: selectedSuggestion?.last_observed_price ?? undefined,
    });

    clear();
    setSelectedSuggestion(null);
  };

  const handleSelectSuggestion = (suggestion: Suggestion) => {
    setQuery(suggestion.name);
    setSelectedSuggestion(suggestion);
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
