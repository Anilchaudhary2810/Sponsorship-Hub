import React from "react";
import { useNavigate } from "react-router-dom";
import { fetchMarketplaceSnapshot, fetchPublicStats } from "../services/api";
import "./LandingPage.css";

const PILLARS = [
  {
    title: "Pipeline Visibility",
    description:
      "Track discovery, approvals, payments, and signatures in one operating view so teams stop losing context across chats and sheets.",
  },
  {
    title: "Three-Sided Fit",
    description:
      "Sponsors, organizers, and creators work in the same workflow with role-based actions designed for real deal coordination.",
  },
  {
    title: "Trust and Control",
    description:
      "KYC, audit trails, payout milestones, and dispute records create a traceable deal history for higher-confidence execution.",
  },
];

const WORKFLOW = [
  {
    step: "01",
    title: "Publish Opportunity",
    text: "Organizers and sponsors create opportunities with clear goals, budgets, and target outcomes.",
  },
  {
    step: "02",
    title: "Align the Right Partners",
    text: "Teams shortlist matching events, campaigns, and creators to avoid low-fit conversations.",
  },
  {
    step: "03",
    title: "Structure the Deal",
    text: "Proposal templates, negotiation logs, and approvals keep decisions aligned before launch.",
  },
  {
    step: "04",
    title: "Execute with Milestones",
    text: "Move from payment to signing to delivery while tracking escrow-style milestone states.",
  },
  {
    step: "05",
    title: "Measure and Repeat",
    text: "Review outcomes and ROI snapshots to scale what works and tighten what does not.",
  },
];

const INDIA_GTM = [
  {
    title: "Campus and Event Network",
    text: "Start with high-frequency college fests, city events, and startup communities where sponsorship demand is constant.",
  },
  {
    title: "Agency and Creator Ops",
    text: "Onboard micro and mid-size agencies that manage creator campaigns and need structured sponsor reporting.",
  },
  {
    title: "Regional City Expansion",
    text: "Launch city-by-city playbooks across Bengaluru, Mumbai, Delhi NCR, Hyderabad, Pune, and Ahmedabad.",
  },
];

const LIVE_NOW = [
  "Role-based marketplace and deal lifecycle",
  "Proposal approvals, negotiations, and milestone tracking",
  "Trust profiles, KYC review workflow, and risk flags",
  "Reporting exports, snapshots, and operational metrics",
  "In-app notifications and collaboration workspaces",
];

const NEXT_UPGRADES = [
  "Real OAuth/API integrations (HubSpot, Slack, Calendar) instead of simulated sync",
  "Production subscription billing flow instead of simulated plan upgrades",
  "KYC file upload and verification pipeline, not URL-only submission",
  "Automated onboarding checklist and guided activation funnel",
  "Public discovery growth loops with SEO-first event and sponsor pages",
];

const LandingPage = () => {
  const navigate = useNavigate();

  const [stats, setStats] = React.useState({ sponsors: 0, events: 0, closedDeals: 0 });
  const [snapshot, setSnapshot] = React.useState({ events: [], campaigns: [] });
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [theme, setTheme] = React.useState(() => localStorage.getItem("app-theme") || "dark");

  React.useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  React.useEffect(() => {
    fetchPublicStats()
      .then((resp) => {
        const data = resp.data;
        setStats({
          sponsors: Number(data.sponsors || 0),
          events: Number(data.events || 0),
          closedDeals: Number(data.closed_deals || 0),
        });
      })
      .catch(() => {});

    fetchMarketplaceSnapshot({ limit: 6 })
      .then((resp) => {
        const data = resp.data || {};
        setSnapshot({
          events: Array.isArray(data.events) ? data.events : [],
          campaigns: Array.isArray(data.campaigns) ? data.campaigns : [],
        });
      })
      .catch(() => {});

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("reveal-on-scroll");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.16 }
    );

    const targets = document.querySelectorAll(".reveal-target");
    targets.forEach((target) => observer.observe(target));

    return () => observer.disconnect();
  }, []);

  const closeMobile = () => setMobileMenuOpen(false);

  return (
    <div className="landing-container">
      <div className="landing-gradient" aria-hidden="true" />
      <div className="landing-grain" aria-hidden="true" />

      <nav className="landing-nav glass">
        <button type="button" className="nav-brand" onClick={() => navigate("/")}>SPONSORHUB</button>

        <div className="nav-links">
          <a href="#why" className="nav-link">Why</a>
          <a href="#workflow" className="nav-link">Workflow</a>
          <a href="#india" className="nav-link">India GTM</a>
          <a href="#readiness" className="nav-link">Readiness</a>
          <button
            type="button"
            className="landing-theme-toggle"
            onClick={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
          <button onClick={() => navigate("/login")} className="btn-primary nav-login-btn">
            Login
          </button>
        </div>

        <button
          className="mobile-menu-toggle"
          onClick={() => setMobileMenuOpen((prev) => !prev)}
          aria-label="Toggle navigation"
        >
          {mobileMenuOpen ? "Close" : "Menu"}
        </button>

        {mobileMenuOpen && (
          <div className="mobile-sidebar glass fade-in">
            <a href="#why" className="nav-link" onClick={closeMobile}>Why</a>
            <a href="#workflow" className="nav-link" onClick={closeMobile}>Workflow</a>
            <a href="#india" className="nav-link" onClick={closeMobile}>India GTM</a>
            <a href="#readiness" className="nav-link" onClick={closeMobile}>Readiness</a>
            <button
              type="button"
              className="landing-theme-toggle mobile-theme-toggle"
              onClick={() => {
                setTheme((prev) => (prev === "dark" ? "light" : "dark"));
                closeMobile();
              }}
            >
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </button>
            <button
              onClick={() => {
                navigate("/login");
                closeMobile();
              }}
              className="btn-primary mobile-login-btn"
            >
              Login
            </button>
          </div>
        )}
      </nav>

      <main>
        <section className="hero-section reveal-target" id="top">
          <p className="hero-kicker">SponsorPitch-grade positioning, built for India</p>
          <h1 className="hero-title">Turn Sponsorship Chaos Into A Predictable Growth Engine.</h1>
          <p className="hero-subtitle">
            SponsorHub helps sponsors, organizers, and creators run one connected deal system from first pitch to payout, with clearer trust, better control, and faster execution.
          </p>
          <div className="hero-btns">
            <button onClick={() => navigate("/register")} className="btn-primary">
              Start Free
            </button>
            <a href="#workflow" className="btn-secondary">
              See Workflow
            </a>
          </div>

          <div className="hero-metrics">
            <article className="hero-metric-card">
              <p className="metric-label">Verified Sponsors</p>
              <h3>{stats.sponsors.toLocaleString()}</h3>
            </article>
            <article className="hero-metric-card">
              <p className="metric-label">Published Events</p>
              <h3>{stats.events.toLocaleString()}</h3>
            </article>
            <article className="hero-metric-card">
              <p className="metric-label">Closed Deals</p>
              <h3>{stats.closedDeals.toLocaleString()}</h3>
            </article>
          </div>
        </section>

        <section className="pillars-section reveal-target" id="why">
          <div className="section-head">
            <p className="section-tag">Why Teams Switch</p>
            <h2>Built Like An Operating Layer, Not A Generic Marketplace.</h2>
          </div>
          <div className="pillars-grid">
            {PILLARS.map((pillar) => (
              <article className="pillar-card" key={pillar.title}>
                <h3>{pillar.title}</h3>
                <p>{pillar.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="workflow-section reveal-target" id="workflow">
          <div className="section-head">
            <p className="section-tag">Execution Framework</p>
            <h2>The End-To-End Flow Your Team Can Actually Run Every Week.</h2>
          </div>
          <div className="workflow-grid">
            {WORKFLOW.map((item) => (
              <article key={item.step} className="workflow-card">
                <p className="workflow-step">{item.step}</p>
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="market-section reveal-target" id="market">
          <div className="market-layout">
            <div className="market-board">
              <div className="market-header">
                <h3>Live Opportunity Board</h3>
                <button className="text-link-btn" onClick={() => navigate("/login")}>View all</button>
              </div>
              <div className="market-columns">
                <div className="market-col">
                  <h4>Recent Events</h4>
                  <div className="market-list">
                    {snapshot.events.slice(0, 4).map((event) => (
                      <article key={event.id} className="market-item">
                        <div>
                          <h5>{event.title}</h5>
                          <p>{[event.city, event.state].filter(Boolean).join(", ") || "Location TBD"}</p>
                        </div>
                        <span>{event.category || "General"}</span>
                      </article>
                    ))}
                    {snapshot.events.length === 0 && <p className="market-empty">No events published yet.</p>}
                  </div>
                </div>

                <div className="market-col">
                  <h4>Latest Campaigns</h4>
                  <div className="market-list">
                    {snapshot.campaigns.slice(0, 4).map((campaign) => (
                      <article key={campaign.id} className="market-item">
                        <div>
                          <h5>{campaign.title}</h5>
                          <p>{campaign.platform_required || "Any platform"}</p>
                        </div>
                        <span>{campaign.status || "open"}</span>
                      </article>
                    ))}
                    {snapshot.campaigns.length === 0 && <p className="market-empty">No campaigns published yet.</p>}
                  </div>
                </div>
              </div>
            </div>

            <aside className="market-side-panel">
              <p className="side-tag">Scale Target</p>
              <h3>What SponsorPitch-level means in practice</h3>
              <ul>
                <li>Fast onboarding to first qualified deal</li>
                <li>Trust signals that reduce sponsor hesitation</li>
                <li>Operational dashboards for repeatable growth</li>
                <li>Reliable integrations with real external systems</li>
              </ul>
              <button className="btn-primary" onClick={() => navigate("/register")}>
                Build With SponsorHub
              </button>
            </aside>
          </div>
        </section>

        <section className="india-section reveal-target" id="india">
          <div className="section-head">
            <p className="section-tag">India Growth Playbook</p>
            <h2>Launch With Focused Segments, Then Expand City By City.</h2>
          </div>
          <div className="india-grid">
            {INDIA_GTM.map((item) => (
              <article key={item.title} className="india-card">
                <h3>{item.title}</h3>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="readiness-section reveal-target" id="readiness">
          <div className="section-head">
            <p className="section-tag">Product Readiness</p>
            <h2>What Is Solid Today Vs What Must Upgrade Before National Scale.</h2>
          </div>
          <div className="readiness-grid">
            <article className="readiness-card">
              <h3>Strong Foundation (Live)</h3>
              <ul>
                {LIVE_NOW.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
            <article className="readiness-card readiness-card-next">
              <h3>Critical Upgrades (Next)</h3>
              <ul>
                {NEXT_UPGRADES.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        <section className="cta-section reveal-target" id="cta">
          <h2>Ready To Grow SponsorHub Into India&apos;s Default Sponsorship OS?</h2>
          <p>Launch with strong operator workflows now, then layer real integrations and growth loops for scale.</p>
          <div className="hero-btns">
            <button onClick={() => navigate("/register")} className="btn-primary cta-btn">
              Create Account
            </button>
            <button onClick={() => navigate("/login")} className="btn-secondary cta-btn-alt">
              Open Dashboard
            </button>
          </div>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="footer-brand-wrap">
          <button type="button" className="nav-brand footer-brand" onClick={() => navigate("/")}>SPONSORHUB</button>
          <p className="footer-copy">Sponsor operations platform for brands, events, and creators.</p>
        </div>
        <div className="footer-links">
          <a className="nav-link-btn" href="mailto:support@sponsorhub.com">Contact</a>
          <a className="nav-link-btn" href="mailto:legal@sponsorhub.com?subject=Privacy%20Policy%20Request">Privacy</a>
          <a className="nav-link-btn" href="mailto:legal@sponsorhub.com?subject=Terms%20Request">Terms</a>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
