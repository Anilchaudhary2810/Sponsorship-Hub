import React from "react";
import "./DashboardStats.css";

const DashboardStats = ({ stats = [] }) => (
  <div className="dashboard-stats-grid">
    {stats.map((stat) => (
      <div key={stat.title} className="dashboard-stat-card">
        <div className="stat-content">
          <p className="dashboard-stat-title">{stat.title}</p>
          <h3 className="dashboard-stat-value">{stat.value}</h3>
        </div>
        <div className="stat-icon-bg"></div>
      </div>
    ))}
  </div>
);

export default DashboardStats;
