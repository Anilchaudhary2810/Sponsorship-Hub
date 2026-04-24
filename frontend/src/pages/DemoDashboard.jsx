import React from "react";
import { useNavigate } from "react-router-dom";
import "./DemoDashboard.css";

const SAMPLE_DATA = {
  sponsor: {
    title: "Sponsor Operations Command Center",
    subtitle: "Track every rupee, milestone, and campaign outcome across your sponsorship portfolio.",
    kpis: [
      { label: "Active Deals", value: "18", trend: "+4 this week" },
      { label: "Budget Committed", value: "INR 42.8L", trend: "74% deployed" },
      { label: "Expected Reach", value: "11.2M", trend: "+19% vs last month" },
      { label: "At-Risk Deals", value: "2", trend: "Needs action" },
    ],
    pipeline: [
      { stage: "Discovery", value: 9 },
      { stage: "Proposal", value: 6 },
      { stage: "Approval", value: 4 },
      { stage: "Payment", value: 3 },
      { stage: "Closed", value: 12 },
    ],
    opportunities: [
      { name: "TechSpark Bengaluru 2026", fit: "High fit", amount: "INR 8L", category: "Campus Tech" },
      { name: "Creator Commerce Summit", fit: "Medium fit", amount: "INR 5L", category: "D2C" },
      { name: "FinTech Youth League", fit: "High fit", amount: "INR 6.5L", category: "Fintech" },
    ],
    actions: ["Approve proposal #D-1842", "Release milestone for Deal #D-1761", "Review campaign ROI export"],
  },
  organizer: {
    title: "Event Partnership Control Room",
    subtitle: "Manage sponsor outreach, deal conversion, and payout milestones from one workspace.",
    kpis: [
      { label: "Live Events", value: "7", trend: "2 launching soon" },
      { label: "Sponsors Contacted", value: "64", trend: "+11 this week" },
      { label: "Deals Closed", value: "21", trend: "33% conversion" },
      { label: "Revenue Secured", value: "INR 31.4L", trend: "Booked" },
    ],
    pipeline: [
      { stage: "Lead List", value: 22 },
      { stage: "Pitch Sent", value: 14 },
      { stage: "Negotiation", value: 9 },
      { stage: "Signing", value: 5 },
      { stage: "Closed", value: 21 },
    ],
    opportunities: [
      { name: "Brand Lead: Nova Mobility", fit: "Ready to pitch", amount: "INR 4.2L", category: "EV" },
      { name: "Brand Lead: PixelPay", fit: "Follow-up", amount: "INR 2.8L", category: "Fintech" },
      { name: "Brand Lead: FitFuel", fit: "Warm lead", amount: "INR 3.5L", category: "Health" },
    ],
    actions: ["Publish Sponsor Deck", "Send 5 sponsor proposals", "Update event milestone board"],
  },
  influencer: {
    title: "Creator Partnership Workspace",
    subtitle: "Discover campaigns, negotiate terms, and track payouts with full visibility.",
    kpis: [
      { label: "Campaign Invites", value: "26", trend: "+7 this week" },
      { label: "Deals in Progress", value: "11", trend: "3 approval pending" },
      { label: "Payouts Received", value: "INR 9.8L", trend: "This quarter" },
      { label: "Avg. Deal Value", value: "INR 89K", trend: "+14%" },
    ],
    pipeline: [
      { stage: "Invited", value: 26 },
      { stage: "Applied", value: 17 },
      { stage: "Negotiating", value: 8 },
      { stage: "Delivering", value: 6 },
      { stage: "Completed", value: 19 },
    ],
    opportunities: [
      { name: "StreetStyle India Campaign", fit: "Brand match", amount: "INR 1.1L", category: "Fashion" },
      { name: "Campus Creator Sprint", fit: "High chance", amount: "INR 75K", category: "Education" },
      { name: "TravelByte Reels Project", fit: "Shortlist", amount: "INR 92K", category: "Travel" },
    ],
    actions: ["Submit media kit update", "Accept campaign brief", "Request milestone release"],
  },
};

const ACTIVITY_FEED = [
  { time: "10:15", text: "Deal #D-1842 moved to Approval" },
  { time: "09:40", text: "KYC profile status updated" },
  { time: "09:05", text: "New opportunity matched by niche" },
  { time: "Yesterday", text: "ROI report exported for April" },
];

const SYSTEM_MODULES = [
  "Deal lifecycle and state tracking",
  "Trust, KYC, and risk signal layer",
  "Revenue milestones and dispute handling",
  "Reporting snapshots and exports",
  "Team collaboration and role permissions",
];

const ROLE_OPTIONS = [
  { id: "sponsor", label: "Sponsor View" },
  { id: "organizer", label: "Organizer View" },
  { id: "influencer", label: "Influencer View" },
];

const DemoDashboard = () => {
  const navigate = useNavigate();
  const [role, setRole] = React.useState("sponsor");
  const roleData = SAMPLE_DATA[role];

  const maxPipelineValue = React.useMemo(
    () => Math.max(...roleData.pipeline.map((stage) => stage.value), 1),
    [roleData.pipeline]
  );

  return (
    <div className="demo-dashboard-page">
      <header className="demo-topbar glass">
        <button type="button" className="demo-brand" onClick={() => navigate("/")}>SPONSORHUB</button>
        <div className="demo-topbar-actions">
          <button type="button" className="demo-link-btn" onClick={() => navigate("/")}>Back to Landing</button>
          <button type="button" className="demo-link-btn" onClick={() => navigate("/login")}>Login</button>
          <button type="button" className="demo-primary-btn" onClick={() => navigate("/register")}>Create Account</button>
        </div>
      </header>

      <main className="demo-content">
        <section className="demo-hero">
          <div className="demo-preview-badge">Interactive Product Preview</div>
          <h1>{roleData.title}</h1>
          <p>{roleData.subtitle}</p>

          <div className="demo-role-switch" role="tablist" aria-label="Role preview switcher">
            {ROLE_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                className={`demo-role-chip ${role === option.id ? "active" : ""}`}
                onClick={() => setRole(option.id)}
              >
                {option.label}
              </button>
            ))}
          </div>
        </section>

        <section className="demo-kpi-grid">
          {roleData.kpis.map((kpi) => (
            <article key={kpi.label} className="demo-kpi-card">
              <p>{kpi.label}</p>
              <h3>{kpi.value}</h3>
              <span>{kpi.trend}</span>
            </article>
          ))}
        </section>

        <section className="demo-main-grid">
          <article className="demo-panel">
            <div className="demo-panel-head">
              <h2>Pipeline Snapshot</h2>
              <span>Live status view</span>
            </div>
            <div className="demo-pipeline-list">
              {roleData.pipeline.map((item) => (
                <div key={item.stage} className="demo-pipeline-row">
                  <div className="demo-stage-meta">
                    <strong>{item.stage}</strong>
                    <span>{item.value}</span>
                  </div>
                  <div className="demo-stage-bar">
                    <div
                      className="demo-stage-fill"
                      style={{ width: `${Math.max((item.value / maxPipelineValue) * 100, 8)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="demo-panel">
            <div className="demo-panel-head">
              <h2>Opportunity Board</h2>
              <span>AI-match placeholder</span>
            </div>
            <div className="demo-opportunity-list">
              {roleData.opportunities.map((item) => (
                <div className="demo-opportunity-item" key={item.name}>
                  <div>
                    <strong>{item.name}</strong>
                    <p>{item.category}</p>
                  </div>
                  <div className="demo-opportunity-meta">
                    <span>{item.fit}</span>
                    <strong>{item.amount}</strong>
                  </div>
                </div>
              ))}
            </div>
          </article>

          <article className="demo-panel">
            <div className="demo-panel-head">
              <h2>Quick Actions</h2>
              <span>Action center</span>
            </div>
            <ul className="demo-list">
              {roleData.actions.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="demo-panel">
            <div className="demo-panel-head">
              <h2>Recent Activity</h2>
              <span>Audit feed</span>
            </div>
            <ul className="demo-activity-list">
              {ACTIVITY_FEED.map((item) => (
                <li key={`${item.time}-${item.text}`}>
                  <span>{item.time}</span>
                  <p>{item.text}</p>
                </li>
              ))}
            </ul>
          </article>

          <article className="demo-panel demo-panel-wide">
            <div className="demo-panel-head">
              <h2>What Users Learn In This System</h2>
              <span>Feature orientation</span>
            </div>
            <ul className="demo-list columns">
              {SYSTEM_MODULES.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>
        </section>
      </main>
    </div>
  );
};

export default DemoDashboard;
