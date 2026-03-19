/* ── ShareModal – Share list invite code ───────────────────────── */

import { useState } from "react";

interface Props {
  inviteCode: string;
  listName: string;
  onClose: () => void;
}

export function ShareModal({ inviteCode, listName, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(inviteCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers
      const input = document.createElement("input");
      input.value = inviteCode;
      document.body.appendChild(input);
      input.select();
      document.execCommand("copy");
      document.body.removeChild(input);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleShareTelegram = () => {
    const text = `Join my shopping list "${listName}" on Hopper Shopper!\n\nInvite code: ${inviteCode}`;
    const url = `https://t.me/share/url?url=${encodeURIComponent(text)}`;
    window.open(url, "_blank");
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="modal-handle" />
        <h3>Share List</h3>
        <p className="share-description">
          Share this invite code with others so they can join your list and
          collaborate in real-time.
        </p>

        <div className="invite-code-display">
          <span className="invite-code-value">{inviteCode}</span>
        </div>

        <div className="modal-actions share-actions">
          <button className="btn btn-secondary" onClick={handleCopy}>
            {copied ? "✓ Copied!" : "📋 Copy Code"}
          </button>
          <button className="btn btn-primary" onClick={handleShareTelegram}>
            ✈️ Share via Telegram
          </button>
        </div>

        <button className="btn btn-secondary share-close-btn" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
