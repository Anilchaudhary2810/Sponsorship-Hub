import React from "react";
import "./EmptyState.css";

const EmptyState = ({ title, description, actionLabel, onAction }) => (
  <div className="empty-state">
    <div className="empty-state-icon" aria-hidden="true" />
    <h4>{title}</h4>
    <p>{description}</p>
    {actionLabel && typeof onAction === "function" && (
      <button type="button" className="empty-state-action" onClick={onAction}>
        {actionLabel}
      </button>
    )}
  </div>
);

export default EmptyState;
