/* ── useDepartments – Debounced department suggestion fetching ── */

import { useCallback, useEffect, useRef, useState } from "react";
import { getDepartments } from "@/services/api";
import type { Department } from "@/types";

export function useDepartments(debounceMs = 200) {
  const [query, setQuery] = useState("");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchDepartments = useCallback(async (q: string) => {
    setIsLoading(true);
    try {
      const results = await getDepartments(q);
      setDepartments(results);
    } catch {
      setDepartments([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    timerRef.current = setTimeout(() => {
      fetchDepartments(query);
    }, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [query, debounceMs, fetchDepartments]);

  const clear = useCallback(() => {
    setQuery("");
    setDepartments([]);
  }, []);

  return { query, setQuery, departments, isLoading, clear };
}
