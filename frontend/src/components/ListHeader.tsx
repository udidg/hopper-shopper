/* ── ListHeader – Top bar with list name, share, join, archive ── */

import { useState } from "react";
import { useListStore } from "@/stores/useListStore";
import { ShareModal } from "./ShareModal";
import { JoinModal } from "./JoinModal";

export function ListHeader() {
  const { activeListDetail, items, archiveBoughtItems } = useListStore();
  const [showShare, setShowShare] = useState(false);
  const [showJoin, setShowJoin] = useState(false);
  const [showArchiveConfirm, setShowArchiveConfirm] = useState(false);

  const scratchedCount = items.filter((i) => i.is_scratched).length;
  const listName = activeListDetail?.name ?? "Shopping List";

  const handleArchive = async () => {
    await archiveBoughtItems();
    setShowArchiveConfirm(false);
  };

  return (
    <>
      <div className="list-header">
        <div className="list-header-title">{listName}</div>
        <div className="list-header-actions">
          {scratchedCount > 0 && (
            <button
              className="header-action-btn archive-btn"
              onClick={() => setShowArchiveConfirm(true)}
              title="Archive bought items"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                <line x1="10" y1="11" x2="10" y2="17" />
                <line x1="14" y1="11" x2="14" y2="17" />
              </svg>
              <span className="archive-badge">{scratchedCount}</span>
            </button>
          )}
          <button
            className="header-action-btn"
            onClick={() => setShowJoin(true)}
            title="Join a list"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="8.5" cy="7" r="4" />
              <line x1="20" y1="8" x2="20" y2="14" />
              <line x1="23" y1="11" x2="17" y2="11" />
            </svg>
          </button>
          <button
            className="header-action-btn"
            onClick={() => setShowShare(true)}
            title="Share list"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="18" cy="5" r="3" />
              <circle cx="6" cy="12" r="3" />
              <circle cx="18" cy="19" r="3" />
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
            </svg>
          </button>
        </div>
      </div>

      {/* Archive confirmation */}
      {showArchiveConfirm && (
        <div className="modal-overlay" onClick={() => setShowArchiveConfirm(false)}>
          <div className="modal-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="modal-handle" />
            <h3>Archive Bought Items</h3>
            <p className="share-description">
              Remove {scratchedCount} checked-off {scratchedCount === 1 ? "item" : "items"} from your list?
              This cannot be undone.
            </p>
            <div className="modal-actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowArchiveConfirm(false)}
              >
                Cancel
              </button>
              <button className="btn btn-danger" onClick={handleArchive}>
                Archive {scratchedCount} {scratchedCount === 1 ? "Item" : "Items"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Share modal */}
      {showShare && activeListDetail && (
        <ShareModal
          inviteCode={activeListDetail.invite_code}
          listName={activeListDetail.name}
          onClose={() => setShowShare(false)}
        />
      )}

      {/* Join modal */}
      {showJoin && <JoinModal onClose={() => setShowJoin(false)} />}
    </>
  );
}
