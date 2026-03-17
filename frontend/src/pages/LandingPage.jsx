
import React from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { fetchPublicStats } from '../services/api';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();

  const [stats, setStats] = React.useState({ sponsors: '500+', events: '1.2k+', capital: '$4M+' });
  const [showBto, setShowBto] = React.useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const audioRef = React.useRef(null);

  React.useEffect(() => {
    // Fetch real stats
    fetchPublicStats()
      .then(resp => {
        const data = resp.data;
        setStats({
          sponsors: `${data.sponsors}+`,
          events: `${data.events}+`,
          capital: data.capital
        });
      })
      .catch(() => {}); // Fallback to defaults

    const observerOptions = {
      threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('reveal-on-scroll');
        }
      });
    }, observerOptions);

    document.querySelectorAll('section').forEach(section => {
      section.style.opacity = '0';
      observer.observe(section);
    });

    return () => observer.disconnect();
  }, []);

  const features = [
    {
      title: "For Sponsors",
      description: "Scale your brand through high-impact events and influencers. Targeted exposure that converts.",
      icon: "🎯"
    },
    {
      title: "For Organizers",
      description: "Secure funding for your next big event. Connect with corporate partners who believe in your vision.",
      icon: "📅"
    },
    {
      title: "For Influencers",
      description: "Monetize your content and reach. Build professional relationships with brands that matter.",
      icon: "✨"
    }
  ];

  const handleAndroidClick = () => {
    setShowBto(true);
    if (!audioRef.current) {
      // Create a small beep or funny sound if possible, 
      // but standard web policy requires user interaction which we have here.
      audioRef.current = new Audio('https://mobcup.fm/browse/ringtones/mp3/0/downloads/time-lagega-meme'); 
    }
    audioRef.current.play().catch(() => {});
    
    toast('Opening the "Android App" experience...', { icon: '🤖' });
    
    setTimeout(() => {
      setShowBto(false);
    }, 5000);
  };

  return (
    <div className="landing-container">
      <div className="landing-bg">
        <div className="orb orb-1"></div>
        <div className="orb orb-2"></div>
      </div>

      <nav className="landing-nav glass">
        <div className="nav-brand">SPONSORHUB</div>
        
        {/* Desktop Links */}
        <div className="nav-links">
          <a href="#features" className="nav-link">Features</a>
          <a href="#about" className="nav-link">About</a>
          <button onClick={() => navigate('/login')} className="btn-primary" style={{ padding: '8px 20px', fontSize: '0.9rem' }}>
            Login
          </button>
        </div>

        {/* Mobile Toggle */}
        <button className="mobile-menu-toggle" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {mobileMenuOpen ? '✕' : '☰'}
        </button>

        {/* Mobile Sidebar */}
        {mobileMenuOpen && (
          <div className="mobile-sidebar glass fade-in">
            <a href="#features" className="nav-link" onClick={() => setMobileMenuOpen(false)}>Features</a>
            <a href="#about" className="nav-link" onClick={() => setMobileMenuOpen(false)}>About</a>
            <button onClick={() => navigate('/login')} className="btn-primary" style={{ width: '100%', marginTop: '1rem' }}>
              Login
            </button>
          </div>
        )}
      </nav>

      <main>
        <section className="hero-section">
          <div className="hero-badge">Next Gen Sponsorship Platform</div>
          <h1 className="hero-title">
            Bridge the Gap Between <br />
            <span>Ambition and Opportunity</span>
          </h1>
          <p className="hero-subtitle">
            The all-in-one ecosystem connecting visionary sponsors, professional organizers, 
            and digital creators to forge meaningful partnerships.
          </p>
          <div className="hero-btns">
            <button onClick={() => navigate('/login')} className="btn-primary">
              Launch Web App
            </button>
            <button 
              className="btn-secondary"
              onClick={handleAndroidClick}
            >
              Android App
              <span className="coming-soon-tag">Coming Soon</span>
            </button>
          </div>

          <div style={{ marginTop: '80px', opacity: 0.6 }}>
            <p style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '2px', marginBottom: '1.5rem' }}>Trusted by Industry Leaders</p>
            <div style={{ display: 'flex', gap: '3rem', justifyContent: 'center', flexWrap: 'wrap', filter: 'grayscale(1) brightness(2)' }}>
              <span style={{ fontWeight: '800', fontSize: '1.2rem' }}>TECHVINE</span>
              <span style={{ fontWeight: '800', fontSize: '1.2rem' }}>GLOBO-CON</span>
              <span style={{ fontWeight: '800', fontSize: '1.2rem' }}>STREAMLY</span>
              <span style={{ fontWeight: '800', fontSize: '1.2rem' }}>EVENT-PRO</span>
            </div>
          </div>
        </section>

        <section id="features" className="features-section">
          {features.map((feature, index) => (
            <div key={index} className="feature-card glass">
              <div className="feature-icon">{feature.icon}</div>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </div>
          ))}
        </section>

        <section id="about" style={{ display: 'none' }}></section>


        <section id="stats" style={{ padding: '80px 5%', textAlign: 'center' }}>
          <div className="landing-stats-grid">
            <div className="stat-item">
              <h2 className="stat-value">{stats.sponsors}</h2>
              <p className="stat-label">Verified Sponsors</p>
            </div>
            <div className="stat-item">
              <h2 className="stat-value">{stats.events}</h2>
              <p className="stat-label">Events Hosted</p>
            </div>
            <div className="stat-item">
              <h2 className="stat-value">{stats.capital}</h2>
              <p className="stat-label">Capital Raised</p>
            </div>
          </div>
        </section>
        <section id="how-it-works" style={{ padding: '100px 5%', background: 'rgba(255,255,255,0.02)' }}>
          <h2 style={{ textAlign: 'center', fontSize: '2.5rem', marginBottom: '4rem' }}>How It Works</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '4rem', maxWidth: '1200px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: '60px', height: '60px', background: 'var(--bg-muted)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', fontSize: '1.5rem', fontWeight: 'bold', border: '1px solid var(--border)' }}>1</div>
              <h4>Create Profile</h4>
              <p style={{ color: 'var(--text-muted)' }}>Sign up as a Sponsor, Organizer, or Influencer and showcase your value.</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: '60px', height: '60px', background: 'var(--bg-muted)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', fontSize: '1.5rem', fontWeight: 'bold', border: '1px solid var(--border)' }}>2</div>
              <h4>Connect & Pitch</h4>
              <p style={{ color: 'var(--text-muted)' }}>Browse opportunities or potential partners and start a conversation.</p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: '60px', height: '60px', background: 'var(--bg-muted)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', fontSize: '1.5rem', fontWeight: 'bold', border: '1px solid var(--border)' }}>3</div>
              <h4>Grow Together</h4>
              <p style={{ color: 'var(--text-muted)' }}>Finalize deals, execute events, and measure your success with our analytics.</p>
            </div>
          </div>
        </section>

        <section id="cta" style={{ padding: '120px 5%', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
          <div className="orb orb-1" style={{ width: '400px', height: '400px', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', opacity: 0.2 }}></div>
          <h2 style={{ fontSize: '3rem', marginBottom: '1.5rem' }}>Ready to elevate your partnerships?</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '1.2rem', marginBottom: '3rem', maxWidth: '600px', margin: '0 auto 3rem' }}>
            Join thousands of professionals already using Sponsor Hub to scale their reach and impact.
          </p>
          <button onClick={() => navigate('/register')} className="btn-primary" style={{ padding: '16px 48px', fontSize: '1.1rem' }}>
            Get Started Today
          </button>
        </section>
      </main>

      <footer style={{ padding: '60px 5% 40px', borderTop: '1px solid var(--border)', textAlign: 'center' }}>
        <div className="nav-brand" style={{ marginBottom: '1.5rem' }}>SPONSORHUB</div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '2rem' }}>
          &copy; {new Date().getFullYear()} Sponsor Hub Inc. All rights reserved.
        </p>
        <div style={{ display: 'flex', gap: '2rem', justifyContent: 'center' }}>
          <button className="nav-link-btn" onClick={() => toast.success("Policy details coming soon!")}>Privacy Policy</button>
          <button className="nav-link-btn" onClick={() => toast.success("Terms coming soon!")}>Terms of Service</button>
          <button className="nav-link-btn" onClick={() => toast.success("Contact: support@sponsorhub.com")}>Contact</button>
        </div>
      </footer>

      {showBto && (
        <div className="bto-overlay" onClick={() => setShowBto(false)}>
           <div className="bto-card glass">
              <div className="bto-avatar">🤖</div>
              <h2>Android App pe Kaam Chal rha h!</h2>
              <p>Thoda sa Time Lagega abhi ...</p>
              <div className="bto-loader"></div>
              <button 
                className="btn-primary" 
                style={{ marginTop: '1rem' }}
                onClick={(e) => { e.stopPropagation(); setShowBto(false); }}
              >
                Theek h bhai!
              </button>
           </div>
        </div>
      )}
    </div>
  );
};

export default LandingPage;
