import React, { useEffect } from "react";
import "./EventDetailModal.css";

const EventDetailModal = ({ event, deal, onClose, onProposeDeal, onChat, formatCurrency }) => {
  // Close on Escape key
  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  if (!event) return null;

  const categoryColors = {
    Tech: "#6366f1", Music: "#ec4899", Sports: "#10b981",
    Business: "#f59e0b", Education: "#06b6d4", Art: "#a855f7",
    Social: "#14b8a6", Other: "#64748b", "Global Event": "#6366f1"
  };
  const catColor = categoryColors[event.category] || "#6366f1";

  return (
    <div className="edm-backdrop" onClick={onClose}>
      <div className="edm-modal" onClick={(e) => e.stopPropagation()}>
        {/* Glow accent */}
        <div className="edm-glow" style={{ background: catColor }} />

        {/* Close button */}
        <button className="edm-close" onClick={onClose}>✕</button>

        {/* Header */}
        <div className="edm-header">
          <span className="edm-category-badge" style={{ background: `${catColor}22`, border: `1px solid ${catColor}55`, color: catColor }}>
            {event.category || "Global Event"}
          </span>
          <h2 className="edm-title">{event.title}</h2>
          <div className="edm-location-row">
            <span className="edm-loc">📍 {event.city}{event.state ? `, ${event.state}` : ""}</span>
            {event.date && <span className="edm-date">📅 {new Date(event.date).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}</span>}
          </div>
        </div>

        {/* Stats grid */}
        <div className="edm-stats-grid">
          <div className="edm-stat">
            <div className="edm-stat-icon">💰</div>
            <div className="edm-stat-value">{formatCurrency ? formatCurrency(event.budget) : `₹${event.budget}`}</div>
            <div className="edm-stat-label">Budget</div>
          </div>
          <div className="edm-stat">
            <div className="edm-stat-icon">👥</div>
            <div className="edm-stat-value">{event.expected_audience ? Number(event.expected_audience).toLocaleString("en-IN") : "—"}</div>
            <div className="edm-stat-label">Expected Audience</div>
          </div>
          <div className="edm-stat">
            <div className="edm-stat-icon">📌</div>
            <div className="edm-stat-value">{event.category || "General"}</div>
            <div className="edm-stat-label">Category</div>
          </div>
          <div className="edm-stat">
            <div className="edm-stat-icon">🗺️</div>
            <div className="edm-stat-value">{event.state || "—"}</div>
            <div className="edm-stat-label">State</div>
          </div>
        </div>

        {/* Description / Summary */}
        {(event.description || event.about) && (
          <div className="edm-section">
            <h4 className="edm-section-title">📋 Summary</h4>
            <p className="edm-description">{event.description || event.about}</p>
          </div>
        )}

        {/* Detailed About - Only show if different from description */}
        {event.about && event.description && event.about !== event.description && (
          <div className="edm-section">
            <h4 className="edm-section-title">🎯 Event Details</h4>
            <p className="edm-description">{event.about}</p>
          </div>
        )}

        {/* Location */}
        {event.location && (
          <div className="edm-section">
            <h4 className="edm-section-title">📍 Venue</h4>
            <p className="edm-description">{event.location}</p>
          </div>
        )}

        {/* Media Gallery */}
        {event.media_items && event.media_items.length > 0 && (
          <div className="edm-section">
            <h4 className="edm-section-title">🖼️ Event Gallery ({event.media_items.length} items)</h4>
            <div className="edm-media-grid">
              {event.media_items.map((item, idx) => (
                <a key={idx} href={item.url} target="_blank" rel="noreferrer" className="edm-media-item" title={item.caption || item.url}>
                  {item.type === "image" ? (
                    <img
                      src={item.url}
                      alt={item.caption || "Gallery item"}
                      className="edm-media-img"
                      onError={(e) => { e.target.src = "https://via.placeholder.com/120x80/1e293b/64748b?text=Image"; }}
                    />
                  ) : item.type === "video" ? (
                    <div className="edm-media-thumb edm-media-video">▶ Video</div>
                  ) : (
                    <div className="edm-media-thumb edm-media-link">🔗 Link</div>
                  )}
                  {item.caption && <span className="edm-media-caption">{item.caption}</span>}
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Deal status badge */}
        {deal && (
          <div className="edm-deal-status">
            <span className="edm-deal-badge">
              ✅ You have an active deal for this event — Status: <strong>{deal.status}</strong>
            </span>
          </div>
        )}

        {/* Actions */}
        <div className="edm-actions">
          {deal ? (
            <>
              <button className="edm-btn-chat" onClick={() => { onChat(deal); onClose(); }}>
                💬 Open Deal Chat
              </button>
              <span className="edm-deal-note">Deal already proposed</span>
            </>
          ) : (
            <button className="edm-btn-propose" onClick={() => { onProposeDeal(event); onClose(); }}>
              🚀 Propose Deal
            </button>
          )}
          <button className="edm-btn-cancel" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default EventDetailModal;
