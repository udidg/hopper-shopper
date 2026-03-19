/* ── JoinModal – Join a list via invite code ───────────────────── */

import { useState } from "react";
import { useListStore } from "@/stores/useListStore";

interface Props {
  onClose: () => void;
}

export function JoinModal({ onClose }: Props) {
  const { joinList, setActiveList } = useListStore();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isJoining, setIsJoining] = useState(false);

  const handleJoin = async () => {
    const trimmed = code.trim();
    if (!trimmed) return;

    setIsJoining(true);
    setError(null);
    try {
      await joinList(trimmed);
      // Auto-select the newly joined list
      const lists = useListStore.getState().lists;
      if (lists.length > 0) {
        setActiveList(lists[0].id);
      }
      onClose();
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { status?: number } };
        if (axiosErr.response?.status === 404) {
          setError("Invalid invite code. Please check and try again.");
        } else if (axiosErr.response?.status === 409) {
          setError("You're already a member of this list.");
        } else {
          setError("Failed to join list. Please try again.");
        }
      } else {
        setError("Failed to join list. Please try again.");
      }
    } finally {
      setIsJoining(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleJoin();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="modal-handle" />
        <h3>Join a List</h3>
        <p className="share-description">
          Enter the invite code shared with you to join a shopping list.
        </p>

        <div className="form-group">
          <label>Invite Code</label>
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Paste invite code here"
            autoFocus
            autoComplete="off"
          />
        </div>

        {error && <div className="join-error">{error}</div>}

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleJoin}
            disabled={isJoining || !code.trim()}
          >
            {isJoining ? "Joining..." : "Join List"}
          </button>
        </div>
      </div>
    </div>
  );
}
