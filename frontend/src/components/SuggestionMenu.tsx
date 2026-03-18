/* ── SuggestionMenu – Floating auto-complete above input ──────── */

import type { Suggestion } from "@/types";

interface Props {
  suggestions: Suggestion[];
  onSelect: (suggestion: Suggestion) => void;
}

export function SuggestionMenu({ suggestions, onSelect }: Props) {
  return (
    <div className="suggestion-menu">
      {suggestions.map((s) => (
        <div
          key={s.id}
          className="suggestion-item"
          onClick={() => onSelect(s)}
        >
          <div>
            <div className="suggestion-name">{s.name}</div>
            {s.default_category && (
              <div className="suggestion-meta">{s.default_category}</div>
            )}
          </div>
          <div className="suggestion-meta">
            {s.preferred_store && <div>🏪 {s.preferred_store}</div>}
            {s.last_observed_price != null && (
              <div>₪{s.last_observed_price.toFixed(2)}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
