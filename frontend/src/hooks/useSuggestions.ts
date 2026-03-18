/* ── useSuggestions – Debounced suggestion fetching ───────────── */

import { useCallback, useEffect, useRef, useState } from "react";
import { getSuggestions } from "@/services/api";
import type { Suggestion } from "@/types";

export function useSuggestions(debounceMs = 300) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.length < 1) {
      setSuggestions([]);
      return;
    }
    setIsLoading(true);
    try {
      const results = await getSuggestions(q);
      setSuggestions(results);
    } catch {
      setSuggestions([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (query.length < 1) {
      setSuggestions([]);
      return;
    }

    timerRef.current = setTimeout(() => {
      fetchSuggestions(query);
    }, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, debounceMs, fetchSuggestions]);

  const clear = useCallback(() => {
    setQuery("");
    setSuggestions([]);
  }, []);

  return { query, setQuery, suggestions, isLoading, clear };
}
