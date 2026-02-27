import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Navbar.css";
import { fetchMyReviews, updateUser } from "../services/api";
import NotificationBell from "./NotificationBell";
import { INDIAN_STATES } from "../utils/constants";

const Navbar = ({ role }) => {
  const navigate = useNavigate();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [showProfilePanel, setShowProfilePanel] = useState(false);
  const [isProfileEditing, setIsProfileEditing] = useState(false);
  const [myReviews, setMyReviews] = useState([]); // reviews RECEIVED by current user
  
  // --- Theme Management ---
  const [theme, setTheme] = useState(() => localStorage.getItem("app-theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const profilePanelRef = useRef(null);

  const [currentUser, setCurrentUser] = useState(() => {
    const raw = localStorage.getItem("currentUser");
    return raw ? JSON.parse(raw) : {};
  });

  const userId = currentUser.id;

  const [profile, setProfile] = useState({
    fullName: currentUser.full_name || "",
    email: currentUser.email || "",
    phone: currentUser.phone || "",
    companyName: currentUser.company_name || "",
    organizationName: currentUser.organization_name || "",
    state: currentUser.state || "",
    city: currentUser.city || "",
    about: currentUser.about || "",
  });

  const [profileForm, setProfileForm] = useState(profile);

  // Sync profile state when currentUser changes
  useEffect(() => {
    const updated = {
      fullName: currentUser.full_name || "",
      email: currentUser.email || "",
      phone: currentUser.phone || "",
      companyName: currentUser.company_name || "",
      organizationName: currentUser.organization_name || "",
      state: currentUser.state || "",
      city: currentUser.city || "",
      about: currentUser.about || "",
    };
    setProfile(updated);
    setProfileForm(updated);
  }, [currentUser]);

  // ── Click-outside to close profile panel ──────────────────────────────────
  useEffect(() => {
    if (!showProfilePanel) return;
    const handleClickOutside = (e) => {
      if (profilePanelRef.current && !profilePanelRef.current.contains(e.target)) {
        setShowProfilePanel(false);
        setIsProfileEditing(false);
      }
    };
    // Small delay so the open-click doesn't immediately close it
    const timerId = setTimeout(() => {
      document.addEventListener("mousedown", handleClickOutside);
    }, 100);
    return () => {
      clearTimeout(timerId);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showProfilePanel]);

  const handleLogout = () => {
    localStorage.removeItem("currentUser");
    localStorage.removeItem("authToken");
    navigate("/login");
  };

  const handleProfileChange = (e) => {
    setProfileForm({ ...profileForm, [e.target.name]: e.target.value });
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    const payload = {
      full_name: profileForm.fullName || null,
      phone: profileForm.phone || null,
      state: profileForm.state || null,
      city: profileForm.city || null,
      about: profileForm.about || null,
    };
    if (role === "sponsor") {
      payload.company_name = profileForm.companyName || null;
    } else {
      payload.organization_name = profileForm.organizationName || null;
    }
    try {
      const resp = await updateUser(userId, payload);
      const updatedUser = resp.data;
      localStorage.setItem("currentUser", JSON.stringify(updatedUser));
      setCurrentUser(updatedUser);
      setIsProfileEditing(false);
      setShowProfilePanel(false);
    } catch {}
  };

  // ── Load reviews RECEIVED by this user (via public profile API) ────────────
  useEffect(() => {
    if (!showProfilePanel || !userId) return;
    (async () => {
      try {
        const token = localStorage.getItem("authToken");
        const resp = await fetch(`http://127.0.0.1:8000/users/${userId}/profile`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!resp.ok) return;
        const data = await resp.json();
        setMyReviews(data.reviews || []);
      } catch {}
    })();
  }, [showProfilePanel, userId]);

  // Average trust score from reviews
  const avgRating = myReviews.length
    ? (myReviews.reduce((s, r) => s + r.rating, 0) / myReviews.length).toFixed(1)
    : (currentUser.trust_score || 0);

  const renderStars = (score) => {
    const full = Math.round(Number(score));
    return Array.from({ length: 5 }, (_, i) => (
      <span key={i} style={{ color: i < full ? "#fbbf24" : "var(--border)", fontSize: 15 }}>★</span>
    ));
  };

  const roleLabel = {
    sponsor: "Company",
    organizer: "Organization",
    influencer: "Organization",
  }[role] || "Company";

  const roleValue = role === "sponsor"
    ? (profile.companyName || "-")
    : (profile.organizationName || "-");

  return (
    <div className="navbar">
      <div className="navbar-left">
        <div className="brand-wrap" onClick={() => {
          if (role === "sponsor") navigate("/sponsor-dashboard");
          else if (role === "organizer") navigate("/organizer-dashboard");
          else navigate("/influencer-dashboard");
        }} style={{ cursor: "pointer" }}>
          <div className="brand-logo" aria-hidden="true">SS</div>
          <h2>Sponsorship Hub</h2>
        </div>
      </div>

      <div className="navbar-center">
        <span className="navbar-role-chip">
          <span className="role-dot" />
          {role === "sponsor" ? "Sponsor Console"
            : role === "organizer" ? "Organizer Command Center"
            : "Influencer Studio"}
        </span>
      </div>

      <div className="navbar-right">
        <NotificationBell />
        {/* Profile Panel — ref attached here for click-outside */}
        <div className="profile-wrap" ref={profilePanelRef}>
          <button
            className="profile-btn"
            onClick={() => {
              setShowProfilePanel(!showProfilePanel);
              setIsProfileEditing(false);
            }}
          >
            <span className="user-icon">👤</span> {profile.fullName || "User Profile"}
          </button>

          {showProfilePanel && (
            <div className="profile-popover">
              {!isProfileEditing ? (
                <>
                  <div className="popover-header">
                    <h4>My Identity</h4>
                    <button className="edit-icon-btn" onClick={() => setIsProfileEditing(true)}>✏️</button>
                  </div>
                  <div className="profile-info-grid">
                    <p><strong>Name:</strong> {profile.fullName || "-"}</p>
                    <p><strong>Email:</strong> {profile.email || "-"}</p>
                    <p><strong>Phone:</strong> {profile.phone || "-"}</p>
                    <p><strong>{roleLabel}:</strong> {roleValue}</p>
                    <p><strong>Location:</strong> {profile.city || profile.state ? `${profile.city}, ${profile.state}` : "-"}</p>
                  </div>

                  {/* ── Trust Score & Feedback — shown for ALL roles ── */}
                  <div className="profile-review-list">
                    <h5>Trust Score &amp; Feedback</h5>
                    <div className="trust-score-row">
                      <div className="trust-stars-mini">{renderStars(avgRating)}</div>
                      <span className="trust-score-num">{Number(avgRating).toFixed(1)} / 5.0</span>
                      <span className="trust-review-count">({myReviews.length} review{myReviews.length !== 1 ? "s" : ""})</span>
                    </div>
                    {myReviews.length === 0 ? (
                      <p className="no-reviews">No reviews received yet.</p>
                    ) : (
                      myReviews.slice(0, 3).map((review) => (
                        <div key={review.id} className="profile-review-item">
                          <div className="review-item-top">
                            <span className="review-item-stars">
                              {Array.from({ length: 5 }, (_, i) => (
                                <span key={i} style={{ color: i < review.rating ? "#fbbf24" : "rgba(255,255,255,0.15)", fontSize: 12 }}>★</span>
                              ))}
                            </span>
                            <span className="review-item-by">{review.reviewer_name}</span>
                          </div>
                          {review.comment && <p className="review-item-comment">"{review.comment}"</p>}
                        </div>
                      ))
                    )}
                  </div>

                  <button type="button" className="profile-inline-btn" onClick={() => setIsProfileEditing(true)}>
                    Modify Profile
                  </button>
                </>
              ) : (
                <form onSubmit={handleSaveProfile} className="profile-edit-form">
                  <h4>Edit Profile Data</h4>
                  <div className="form-scroll">
                    <label>Full Name</label>
                    <input type="text" name="fullName" value={profileForm.fullName} onChange={handleProfileChange} required />
                    <label>Phone Number</label>
                    <input type="text" name="phone" value={profileForm.phone} onChange={handleProfileChange} />
                    {role === "sponsor" ? (
                      <>
                        <label>Company Name</label>
                        <input type="text" name="companyName" value={profileForm.companyName} onChange={handleProfileChange} />
                      </>
                    ) : (
                      <>
                        <label>Organization Name</label>
                        <input type="text" name="organizationName" value={profileForm.organizationName} onChange={handleProfileChange} />
                      </>
                    )}
                    <label>State</label>
                    <select name="state" value={profileForm.state} onChange={handleProfileChange}>
                      <option value="">Select State</option>
                      {INDIAN_STATES.filter(s => s !== "All States").map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                    <label>City</label>
                    <input type="text" name="city" value={profileForm.city} onChange={handleProfileChange} />
                    <label>About Bio</label>
                    <textarea name="about" value={profileForm.about} onChange={handleProfileChange} rows="2" />
                  </div>
                  <div className="profile-popover-actions">
                    <button type="button" className="profile-cancel-btn" onClick={() => setIsProfileEditing(false)}>Cancel</button>
                    <button type="submit" className="profile-save-btn">Save Changes</button>
                  </div>
                </form>
              )}
            </div>
          )}
        </div>

        <div className="logout-wrap">
          <button className="logout-btn" onClick={() => setShowLogoutConfirm(!showLogoutConfirm)}>
            Log out
          </button>
          {showLogoutConfirm && (
            <div className="logout-popover">
              <p>Sign out of session?</p>
              <div className="logout-actions">
                <button type="button" className="logout-cancel-btn" onClick={() => setShowLogoutConfirm(false)}>Stay</button>
                <button type="button" className="logout-confirm-btn" onClick={handleLogout}>Logout</button>
              </div>
            </div>
          )}
        </div>

        <button className="theme-toggle-btn" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
          {theme === 'dark' ? '🌞' : '🌙'}
        </button>
      </div>
    </div>
  );
};

export default Navbar;
