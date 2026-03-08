
import React from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import './LandingPage.css';

const LandingPage = () => {
  const navigate = useNavigate();

  React.useEffect(() => {
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
          <a href="#about" className="nav-link">About</a>
          <button onClick={() => navigate('/login')} className="btn-primary" style={{ padding: '8px 20px', fontSize: '0.9rem' }}>
            Login
          </button>
        </div>
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
              onClick={() => toast.success('Android App is in development. Stay tuned!', { icon: '📱' })}
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

        <section id="stats" style={{ padding: '80px 5%', textAlign: 'center' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '3rem', maxWidth: '1000px', margin: '0 auto' }}>
            <div>
              <h2 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>500+</h2>
              <p style={{ color: 'var(--text-muted)' }}>Verified Sponsors</p>
            </div>
            <div>
              <h2 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>1.2k+</h2>
              <p style={{ color: 'var(--text-muted)' }}>Events Hosted</p>
            </div>
            <div>
              <h2 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>$4M+</h2>
              <p style={{ color: 'var(--text-muted)' }}>Capital Raised</p>
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
          <a href="#" className="nav-link">Privacy Policy</a>
          <a href="#" className="nav-link">Terms of Service</a>
          <a href="#" className="nav-link">Contact</a>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
