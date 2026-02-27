import React, { useState } from "react";
import "./MediaPortfolio.css";

const MediaPortfolio = ({ items = [], onAdd, onDelete, canEdit = false, title = "Media Gallery" }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newItem, setNewItem] = useState({ url: "", caption: "", type: "image" });

  const handleAdd = () => {
    if (!newItem.url.trim()) return;
    onAdd && onAdd(newItem);
    setNewItem({ url: "", caption: "", type: "image" });
    setShowAddForm(false);
  };

  const isValidUrl = (url) => {
    try { new URL(url); return true; } catch { return false; }
  };

  return (
    <div className="media-portfolio-section">
      <div className="media-portfolio-header">
        <div className="media-header-left">
          <h2 className="media-title">🖼️ {title}</h2>
          <span className="media-count-badge">{items.length} Items</span>
        </div>
        {canEdit && (
          <button className="add-media-btn" onClick={() => setShowAddForm(!showAddForm)}>
            {showAddForm ? "✕ Cancel" : "+ Add Media"}
          </button>
        )}
      </div>

      {/* Add Form */}
      {showAddForm && (
        <div className="add-media-form glass-card">
          <h4>Add Portfolio Item</h4>
          <div className="add-media-fields">
            <div className="field-group">
              <label>Type</label>
              <select
                value={newItem.type}
                onChange={(e) => setNewItem({ ...newItem, type: e.target.value })}
                className="media-select"
              >
                <option value="image">🖼️ Photo/Poster</option>
                <option value="video">🎬 Video URL</option>
                <option value="link">🔗 External Link</option>
              </select>
            </div>
            <div className="field-group">
              <label>URL</label>
              <input
                type="url"
                placeholder="https://..."
                value={newItem.url}
                onChange={(e) => setNewItem({ ...newItem, url: e.target.value })}
                className="media-input"
              />
            </div>
            <div className="field-group">
              <label>Caption</label>
              <input
                type="text"
                placeholder="Describe this item..."
                value={newItem.caption}
                onChange={(e) => setNewItem({ ...newItem, caption: e.target.value })}
                className="media-input"
              />
            </div>
          </div>
          <div className="add-form-actions">
            {newItem.url && isValidUrl(newItem.url) && (
              <div className="url-preview">
                <img
                  src={newItem.url}
                  alt="Preview"
                  className="url-preview-img"
                  onError={(e) => { e.target.style.display = "none"; }}
                />
              </div>
            )}
            <button className="save-media-btn" onClick={handleAdd} disabled={!newItem.url}>
              Save to Portfolio
            </button>
          </div>
        </div>
      )}

      {/* Gallery Grid */}
      {items.length === 0 ? (
        <div className="media-empty-state">
          <div className="media-empty-icon">📷</div>
          <p>No media items yet.{canEdit ? " Add event photos, posters, or links to showcase your work!" : " Check back later."}</p>
        </div>
      ) : (
        <div className="media-gallery-grid">
          {items.map((item, index) => (
            <div key={index} className="media-gallery-item">
              {item.type === "image" ? (
                <a href={item.url} target="_blank" rel="noreferrer" className="media-item-link">
                  <img
                    src={item.url}
                    alt={item.caption || "Portfolio item"}
                    className="media-gallery-img"
                    loading="lazy"
                    onError={(e) => {
                      e.target.src = "https://via.placeholder.com/320x200/1e293b/64748b?text=Image+Not+Found";
                    }}
                  />
                  <div className="media-overlay">
                    <span className="media-overlay-icon">🔍</span>
                  </div>
                </a>
              ) : item.type === "video" ? (
                <a href={item.url} target="_blank" rel="noreferrer" className="media-item-link video-item">
                  <div className="video-thumb">
                    <span className="play-icon">▶</span>
                    <span className="video-label">Watch Video</span>
                  </div>
                </a>
              ) : (
                <a href={item.url} target="_blank" rel="noreferrer" className="media-item-link link-item">
                  <div className="link-thumb">
                    <span className="link-icon">🔗</span>
                    <span className="link-url">{item.url.substring(0, 40)}...</span>
                  </div>
                </a>
              )}
              {item.caption && <p className="media-caption">{item.caption}</p>}
              {canEdit && (
                <button className="delete-media-btn" onClick={() => onDelete && onDelete(index)}>✕</button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MediaPortfolio;
