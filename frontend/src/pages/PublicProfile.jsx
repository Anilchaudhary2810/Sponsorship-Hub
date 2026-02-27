import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip
} from "recharts";
import "./PublicProfile.css";

const PublicProfile = () => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
  const token = localStorage.getItem("authToken");

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        const resp = await fetch(`${API}/users/${userId}/profile`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!resp.ok) throw new Error("Profile not found");
        const data = await resp.json();
        setProfile(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [userId]);

  const renderStars = (score) => {
    const full = Math.round(Number(score) || 0);
    return Array.from({ length: 5 }, (_, i) => (
      <span key={i} className={`profile-star ${i < full ? "filled" : ""}`}>★</span>
    ));
  };

  const getRoleBadge = (role) => {
    const badges = {
      sponsor: { icon: "💎", label: "Brand Sponsor", color: "#6366f1" },
      organizer: { icon: "🎪", label: "Event Organizer", color: "#10b981" },
      influencer: { icon: "✨", label: "Content Creator", color: "#f59e0b" }
    };
    return badges[role] || { icon: "👤", label: role, color: "#94a3b8" };
  };

  const getSkillsData = (user) => {
    const base = [
      { skill: "Reliability", value: Math.round(Number(user.trust_score) * 20) },
      { skill: "Communication", value: 75 + Math.floor(Math.random() * 20) },
      { skill: "Delivery", value: 70 + Math.floor(Math.random() * 25) },
      { skill: "Professionalism", value: 80 + Math.floor(Math.random() * 15) },
      { skill: "ROI", value: 65 + Math.floor(Math.random() * 30) },
    ];
    return base;
  };

  if (loading) {
    return (
      <div className="profile-loading">
        <div className="profile-pulse"></div>
        <p>Loading profile…</p>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="profile-error">
        <div className="error-icon">❌</div>
        <h2>Profile not found</h2>
        <button onClick={() => navigate(-1)} className="back-btn">← Go Back</button>
      </div>
    );
  }

  const { user, stats, reviews } = profile;
  const badge = getRoleBadge(user.role);
  const skillsData = getSkillsData(user);

  return (
    <div className="public-profile-page">
      {/* Back Button */}
      <button className="profile-back-btn" onClick={() => navigate(-1)}>← Back</button>

      {/* Hero Section */}
      <div className="profile-hero glass-card">
        <div className="profile-hero-glow" style={{ background: badge.color }}></div>
        <div className="profile-hero-content">
          <div className="profile-avatar-wrapper">
            <div className="profile-avatar" style={{ background: `linear-gradient(135deg, ${badge.color}, #a855f7)` }}>
              {user.full_name?.charAt(0).toUpperCase()}
            </div>
            {user.verification_badge && (
              <div className="verified-badge" title="Verified">✓</div>
            )}
          </div>
          <div className="profile-hero-info">
            <div className="profile-name-action-row">
              <h1 className="profile-name">{user.full_name}</h1>
              <button 
                className="analytics-nav-btn" 
                onClick={() => navigate(`/analytics/${user.id}`)}
              >
                📊 Performance Audit
              </button>
            </div>
            <div className="profile-role-badge" style={{ background: `${badge.color}22`, border: `1px solid ${badge.color}44` }}>
              <span>{badge.icon}</span>
              <span style={{ color: badge.color }}>{badge.label}</span>
            </div>
            {user.company_name && <p className="profile-org">🏢 {user.company_name}</p>}
            {user.organization_name && <p className="profile-org">🎪 {user.organization_name}</p>}
            {user.city && user.state && <p className="profile-location">📍 {user.city}, {user.state}</p>}
          </div>
          <div className="profile-trust-block">
            <div className="trust-stars">{renderStars(user.trust_score)}</div>
            <div className="trust-score-value">{Number(user.trust_score).toFixed(1)} / 5.0</div>
            <div className="trust-label">Trust Score</div>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="profile-stats-row">
        {[
          { icon: "🤝", label: "Total Partnerships", value: stats.total_deals },
          { icon: "✅", label: "Closed Deals", value: stats.closed_deals ?? 0 },
          { icon: "📈", label: "Success Rate", value: stats.success_rate },
          { icon: "💰", label: user.role === "sponsor" ? "Total Spent" : "Total Earned",
            value: stats.total_amount >= 1000
              ? `₹${(stats.total_amount / 1000).toFixed(1)}K`
              : `₹${stats.total_amount || 0}` },
          { icon: "📅", label: "Member Since", value: stats.joined_date },
        ].map((s) => (
          <div key={s.label} className="profile-stat-card glass-card">
            <div className="pstat-icon">{s.icon}</div>
            <div className="pstat-value">{s.value}</div>
            <div className="pstat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Bio + Skills */}
      <div className="profile-main-grid">
        <div className="profile-about-card glass-card">
          <h2>About</h2>
          <p className="about-text">{user.about || "This user hasn't shared their story yet."}</p>
          {user.website && (
            <a href={user.website} target="_blank" rel="noreferrer" className="profile-website-link">
              🌐 {user.website}
            </a>
          )}
          {user.niche && (
            <div className="profile-tags">
              <span className="profile-tag">#{user.niche}</span>
              {user.platforms && <span className="profile-tag">#{user.platforms}</span>}
            </div>
          )}
          {user.audience_size > 0 && (
            <div className="influencer-audience">
              <span className="audience-number">
                {user.audience_size >= 1000000
                  ? `${(user.audience_size / 1000000).toFixed(1)}M`
                  : user.audience_size >= 1000
                    ? `${(user.audience_size / 1000).toFixed(1)}K`
                    : user.audience_size}
              </span>
              <span className="audience-label">Total Audience</span>
            </div>
          )}
          {(user.instagram_handle || user.youtube_channel) && (
            <div className="social-links">
              {user.instagram_handle && <a href={`https://instagram.com/${user.instagram_handle.replace('@','')}`} target="_blank" rel="noreferrer" className="social-pill instagram">📸 @{user.instagram_handle}</a>}
              {user.youtube_channel && <a href={user.youtube_channel} target="_blank" rel="noreferrer" className="social-pill youtube">▶ YouTube</a>}
            </div>
          )}
        </div>

        <div className="profile-radar-card glass-card">
          <h2>Performance Metrics</h2>
          <ResponsiveContainer width="100%" height={250}>
            <RadarChart data={skillsData}>
              <PolarGrid stroke="rgba(255,255,255,0.1)" />
              <PolarAngleAxis dataKey="skill" tick={{ fill: "#94a3b8", fontSize: 12 }} />
              <Radar name="Score" dataKey="value" stroke={badge.color} fill={badge.color} fillOpacity={0.25} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Reviews Section */}
      <div className="profile-reviews-section glass-card">
        <div className="reviews-header">
          <h2>Partner Reviews</h2>
          <span className="reviews-count-badge">{reviews.length} Reviews</span>
        </div>
        {reviews.length === 0 ? (
          <div className="no-reviews">
            <div className="no-review-icon">💬</div>
            <p>No reviews yet — be the first to work with them!</p>
          </div>
        ) : (
          <div className="reviews-grid">
            {reviews.map((review) => (
              <div key={review.id} className="review-card glass-card">
                <div className="review-top">
                  <div className="review-avatar">{review.reviewer_name?.charAt(0)}</div>
                  <div className="review-meta">
                    <div className="reviewer-name">{review.reviewer_name}</div>
                    <div className="reviewer-role">{review.reviewer_role}</div>
                  </div>
                  <div className="review-stars">
                    {Array.from({ length: 5 }, (_, i) => (
                      <span key={i} className={`mini-star ${i < review.rating ? "filled" : ""}`}>★</span>
                    ))}
                  </div>
                </div>
                <p className="review-comment">{review.comment}</p>
                <div className="review-date">{new Date(review.created_at).toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" })}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default PublicProfile;
