import React from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchMarketplaceSnapshot, fetchPublicStats } from '../services/api';
import './LandingPage.css';

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

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  React.useEffect(() => {
    fetchPublicStats()
      .then(resp => {
        const data = resp.data;
        setStats({
          sponsors: Number(data.sponsors || 0),
          events: Number(data.events || 0),
          closedDeals: Number(data.closed_deals || 0),
        });
      })
      .catch(() => {});

    fetchMarketplaceSnapshot({ limit: 6 })
      .then(resp => {
        const data = resp.data || {};
        setSnapshot({
          events: Array.isArray(data.events) ? data.events : [],
          campaigns: Array.isArray(data.campaigns) ? data.campaigns : [],
        });
      })
      .catch(() => {});

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal-on-scroll');
        }
      });
    }, { threshold: 0.15 });

    document.querySelectorAll('section').forEach(section => {
      section.style.opacity = '0';
      observer.observe(section);
    });

    return () => observer.disconnect();
  }, []);

  const features = [
    {
      title: 'For Sponsors',
      description: 'Find vetted events and creators aligned with your goals, then deploy sponsorship capital with transparency.'
    },
    {
      title: 'For Organizers',
      description: 'Publish event opportunities, attract serious sponsors, and manage the full partnership lifecycle in one place.'
    },
    {
      title: 'For Influencers',
      description: 'Get matched with campaigns and event deals that fit your audience profile and long-term brand direction.'
    }
  ];

  return (
    <div className="landing-container">
      <div className="landing-bg">
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
      </div>

      <nav className="landing-nav glass">
        <div className="nav-brand">SPONSORHUB</div>

        <div className="nav-links">
          <a href="#features" className="nav-link">Features</a>
          <a href="#how-it-works" className="nav-link">Process</a>
          <a href="#stats" className="nav-link">Proof</a>
          <button
            type="button"
            className="landing-theme-toggle"
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? "\u2600" : "\u263E"}
          </button>
          <button onClick={() => navigate('/login')} className="btn-primary nav-login-btn">
            Login
          </button>
        </div>

        <button className="mobile-menu-toggle" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {mobileMenuOpen ? 'X' : 'Menu'}
        </button>

        {mobileMenuOpen && (
          <div className="mobile-sidebar glass fade-in">
            <a href="#features" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Features</a>
            <a href="#how-it-works" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Process</a>
            <a href="#stats" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Proof</a>
            <button type="button" className="landing-theme-toggle mobile-theme-toggle" onClick={toggleTheme}>
              {theme === "dark" ? "Light Mode" : "Dark Mode"}
            </button>
            <button onClick={() => navigate('/login')} className="btn-primary mobile-login-btn">
              Login
            </button>
          </div>
        )}
      </nav>

      <main>
        <section className="hero-section">
          <div className="hero-badge">Sponsor operations, rethought</div>
          <h1 className="hero-title">Built for teams who take partnerships seriously.</h1>
          <p className="hero-subtitle">
            SponsorHub connects sponsors, organizers, and creators through a workflow designed for clarity:
            discover, align, contract, execute, and review.
          </p>
          <div className="hero-btns">
            <button onClick={() => navigate('/login')} className="btn-primary">
              Launch Web App
            </button>
            <button className="btn-secondary" onClick={() => navigate('/register')}>Create Account</button>
          </div>

          <div className="hero-trust">
            <p className="trust-label">Live marketplace snapshot</p>
            <div className="trust-brands">
              <span>{snapshot.events.length} Recent Events</span>
              <span>{snapshot.campaigns.length} Active Campaigns</span>
              <span>{stats.sponsors} Verified Sponsors</span>
            </div>
          </div>
        </section>

        <section id="features" className="features-section">
          {features.map((feature, index) => (
            <div key={index} className="feature-card glass">
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </section>

        <section id="stats" className="stats-section">
          <div className="landing-stats-grid">
            <div className="stat-item">
              <h2 className="stat-value">{stats.sponsors.toLocaleString()}</h2>
              <p className="stat-label">Verified Sponsors</p>
            </div>
            <div className="stat-item">
              <h2 className="stat-value">{stats.events.toLocaleString()}</h2>
              <p className="stat-label">Events Hosted</p>
            </div>
            <div className="stat-item">
              <h2 className="stat-value">{stats.closedDeals.toLocaleString()}</h2>
              <p className="stat-label">Closed Deals</p>
            </div>
          </div>
        </section>

        <section id="marketplace" className="marketplace-section">
          <div className="marketplace-columns">
            <div className="market-col">
              <div className="market-col-header">
                <h3>Recent Events</h3>
                <button className="text-link-btn" onClick={() => navigate('/login')}>View all</button>
              </div>
              <div className="market-list">
                {snapshot.events.slice(0, 4).map((event) => (
                  <article key={event.id} className="market-item">
                    <div>
                      <h4>{event.title}</h4>
                      <p>{[event.city, event.state].filter(Boolean).join(', ') || 'Location TBD'}</p>
                    </div>
                    <span>{event.category || 'General'}</span>
                  </article>
                ))}
                {snapshot.events.length === 0 && <p className="market-empty">No events published yet.</p>}
              </div>
            </div>

            <div className="market-col">
              <div className="market-col-header">
                <h3>Latest Campaigns</h3>
                <button className="text-link-btn" onClick={() => navigate('/login')}>View all</button>
              </div>
              <div className="market-list">
                {snapshot.campaigns.slice(0, 4).map((campaign) => (
                  <article key={campaign.id} className="market-item">
                    <div>
                      <h4>{campaign.title}</h4>
                      <p>{campaign.platform_required || 'Any platform'}</p>
                    </div>
                    <span>{campaign.status || 'open'}</span>
                  </article>
                ))}
                {snapshot.campaigns.length === 0 && <p className="market-empty">No campaigns published yet.</p>}
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="how-section">
          <h2 className="section-title">How It Works</h2>
          <div className="how-grid">
            <div className="how-card">
              <div className="how-step">1</div>
              <h4>Create Profile</h4>
              <p>Set up your sponsor, organizer, or creator profile with clear objectives and proof points.</p>
            </div>
            <div className="how-card">
              <div className="how-step">2</div>
              <h4>Connect and Pitch</h4>
              <p>Discover opportunities, shortlist the right partners, and align deliverables in structured deals.</p>
            </div>
            <div className="how-card">
              <div className="how-step">3</div>
              <h4>Execute and Measure</h4>
              <p>Track payment, signing, and outcomes so every partnership drives repeatable growth.</p>
            </div>
          </div>
        </section>

        <section id="cta" className="cta-section">
          <h2>Ready to run partnerships with more confidence?</h2>
          <p>Move from disconnected conversations to a single system that your whole team can trust.</p>
          <button onClick={() => navigate('/register')} className="btn-primary cta-btn">
            Get Started Today
          </button>
        </section>
      </main>

      <footer className="landing-footer">
        <div className="nav-brand footer-brand">SPONSORHUB</div>
        <p className="footer-copy">&copy; {new Date().getFullYear()} Sponsor Hub Inc. All rights reserved.</p>
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
