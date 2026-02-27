import React, { useMemo } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, Legend
} from "recharts";
import "./AnalyticsPanel.css";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#06b6d4"];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="analytics-tooltip">
        <p className="tooltip-label">{label}</p>
        {payload.map((p, i) => (
          <p key={i} style={{ color: p.color }}>
            {p.name}: <strong>{p.value}</strong>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const AnalyticsPanel = ({ 
  deals = [], 
  events = [], 
  campaigns = [], 
  role = "sponsor", 
  title = "Performance Insights",
  subtitle = "Your growth at a glance" 
}) => {
  // Build monthly deal data from real deals
  const monthlyData = useMemo(() => {
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const now = new Date();
    const last6 = Array.from({ length: 6 }, (_, i) => {
      const d = new Date(now.getFullYear(), now.getMonth() - (5 - i), 1);
      return { month: months[d.getMonth()], year: d.getFullYear(), monthIdx: d.getMonth() };
    });

    return last6.map(({ month, year, monthIdx }) => {
      const monthDeals = deals.filter(deal => {
        const d = new Date(deal.created_at || deal.updated_at || Date.now());
        return d.getMonth() === monthIdx && d.getFullYear() === year;
      });
      const revenue = monthDeals
        .filter(d => d.status === "closed" || d.payment_done)
        .reduce((sum, d) => sum + (Number(d.paymentAmount || d.payment_amount) || 0), 0);
      return {
        month,
        deals: monthDeals.length,
        revenue: Math.round(revenue / 1000),
        closed: monthDeals.filter(d => d.status === "closed").length
      };
    });
  }, [deals]);

  // Deal status distribution
  const statusData = useMemo(() => {
    const statusMap = {};
    deals.forEach(d => {
      statusMap[d.status] = (statusMap[d.status] || 0) + 1;
    });
    return Object.entries(statusMap).map(([name, value]) => ({ name, value }));
  }, [deals]);

  // Total metrics
  const totalRevenue = deals
    .filter(d => d.status === "closed" || d.payment_done || d.paymentDone)
    .reduce((s, d) => s + (Number(d.paymentAmount || d.payment_amount) || 0), 0);
  const closedDeals = deals.filter(d => d.status === "closed").length;
  const pendingDeals = deals.filter(d => !["closed", "rejected"].includes(d.status)).length;

  return (
    <div className="analytics-panel">
      <div className="analytics-header">
        <h2 className="analytics-title">📊 {title}</h2>
        <span className="analytics-subtitle">{subtitle}</span>
      </div>

      {/* Top KPI Cards */}
      <div className="analytics-kpi-row">
        <div className="kpi-card kpi-indigo">
          <div className="kpi-icon">{role === "sponsor" ? "💸" : "💰"}</div>
          <div className="kpi-info">
            <div className="kpi-value">₹{totalRevenue >= 1000 ? `${(totalRevenue/1000).toFixed(1)}K` : totalRevenue}</div>
            <div className="kpi-label">{role === "sponsor" ? "Total Spent" : "Total Earned"}</div>
          </div>
          <div className="kpi-trend up">{role === "sponsor" ? "▼ Spent" : "▲ Live"}</div>
        </div>
        <div className="kpi-card kpi-emerald">
          <div className="kpi-icon">🤝</div>
          <div className="kpi-info">
            <div className="kpi-value">{closedDeals}</div>
            <div className="kpi-label">Closed Deals</div>
          </div>
          <div className="kpi-trend up">✓ Done</div>
        </div>
        <div className="kpi-card kpi-amber">
          <div className="kpi-icon">⚡</div>
          <div className="kpi-info">
            <div className="kpi-value">{pendingDeals}</div>
            <div className="kpi-label">Active Deals</div>
          </div>
          <div className="kpi-trend">In Progress</div>
        </div>
        <div className="kpi-card kpi-pink">
          <div className="kpi-icon">{role === "organizer" ? "🎪" : role === "sponsor" ? "📢" : "✨"}</div>
          <div className="kpi-info">
            <div className="kpi-value">{role === "organizer" ? events.length : campaigns.length}</div>
            <div className="kpi-label">{role === "organizer" ? "My Events" : "My Campaigns"}</div>
          </div>
          <div className="kpi-trend">Total</div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="analytics-charts-row">
        {/* Area Chart */}
        <div className="chart-card glass-card">
          <h3 className="chart-title">Deal Activity (Last 6 Months)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={monthlyData} margin={{ top: 10, right: 10, left: -30, bottom: 0 }}>
              <defs>
                <linearGradient id="colorDeals" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="month" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="deals" name="Deals" stroke="#6366f1" strokeWidth={2} fill="url(#colorDeals)" />
              <Area type="monotone" dataKey="revenue" name={role === "sponsor" ? "Spent (₹K)" : "Earned (₹K)"} stroke="#10b981" strokeWidth={2} fill="url(#colorRevenue)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart */}
        <div className="chart-card glass-card">
          <h3 className="chart-title">Deal Status Breakdown</h3>
          {statusData.length === 0 ? (
            <div className="chart-empty">No deals yet</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v, n) => [v, n]} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Bar Chart (monthly closed deals) */}
        <div className="chart-card glass-card">
          <h3 className="chart-title">Closed Deals by Month</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={monthlyData} margin={{ top: 10, right: 10, left: -30, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="month" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="closed" name="Closed" fill="#6366f1" radius={[6, 6, 0, 0]}>
                {monthlyData.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsPanel;
