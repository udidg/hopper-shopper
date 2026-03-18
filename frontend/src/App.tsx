import { useEffect } from "react";
import { useAuthStore } from "@/stores/useAuthStore";
import { useListStore } from "@/stores/useListStore";
import { useWebSocket } from "@/hooks/useWebSocket";
import { GroceryList } from "@/components/GroceryList";
import { InputBar } from "@/components/InputBar";

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        initData: string;
        ready: () => void;
        expand: () => void;
        MainButton: {
          show: () => void;
          hide: () => void;
          setText: (text: string) => void;
          onClick: (cb: () => void) => void;
        };
      };
    };
  }
}

export default function App() {
  const { isAuthenticated, isLoading: authLoading, login } = useAuthStore();
  const { lists, activeListId, isLoading, fetchLists, setActiveList, createList } =
    useListStore();

  // ── WebSocket connection for real-time updates ────────────────
  useWebSocket(activeListId);

  // ── Telegram SDK init & auth ──────────────────────────────────
  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();

      if (tg.initData && !isAuthenticated) {
        login(tg.initData);
      }
    }
  }, [isAuthenticated, login]);

  // ── Fetch lists after auth ────────────────────────────────────
  useEffect(() => {
    if (isAuthenticated) {
      fetchLists();
    }
  }, [isAuthenticated, fetchLists]);

  // ── Auto-select first list ────────────────────────────────────
  useEffect(() => {
    if (lists.length > 0 && !activeListId) {
      setActiveList(lists[0].id);
    }
  }, [lists, activeListId, setActiveList]);

  // ── Loading state ─────────────────────────────────────────────
  if (authLoading) {
    return (
      <div className="empty-state">
        <div className="emoji">🔐</div>
        <p>Authenticating with Telegram...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="empty-state">
        <div className="emoji">🛒</div>
        <p>
          Open this app from Telegram
          <br />
          to get started!
        </p>
      </div>
    );
  }

  // ── No lists yet ──────────────────────────────────────────────
  if (lists.length === 0 && !isLoading) {
    return (
      <div className="app-container">
        <div className="empty-state">
          <div className="emoji">📝</div>
          <p>No grocery lists yet!</p>
          <button
            className="btn btn-primary"
            style={{ marginTop: 16, padding: "12px 24px", borderRadius: 10, border: "none", fontSize: 16, cursor: "pointer", backgroundColor: "var(--app-button)", color: "var(--app-button-text)" }}
            onClick={async () => {
              const list = await createList("My Grocery List");
              setActiveList(list.id);
            }}
          >
            Create Your First List
          </button>
        </div>
      </div>
    );
  }

  // ── Main view ─────────────────────────────────────────────────
  return (
    <div className="app-container">
      <GroceryList />
      <InputBar />
    </div>
  );
}
