import React from "react";
import "./QuickActionsBar.css";

const QuickActionsBar = ({ actions = [] }) => {
  if (!actions.length) return null;
  return (
    <div className="quick-actions-bar">
      {actions.map((action) => (
        <button
          key={action.key}
          type="button"
          className={`quick-action-btn ${action.tone || "default"}`}
          onClick={action.onClick}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
};

export default QuickActionsBar;
