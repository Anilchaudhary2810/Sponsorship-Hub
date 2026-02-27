import React from "react";
import "./EmptyState.css";

const EmptyState = ({ title, description }) => (
  <div className="empty-state">
    <div className="empty-state-icon" aria-hidden="true">
      📭
    </div>
    <h4>{title}</h4>
    <p>{description}</p>
  </div>
);

export default EmptyState;
