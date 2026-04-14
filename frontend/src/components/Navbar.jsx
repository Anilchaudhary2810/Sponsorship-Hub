import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Navbar.css";
import { updateUser, fetchUserProfile, fetchMyBilling, logoutUser } from "../services/api";
import { clearAccessToken } from "../api/api";
import NotificationBell from "./NotificationBell";
import { INDIAN_STATES } from "../utils/constants";

const Navbar = ({ role }) => {
  const navigate = useNavigate();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [showProfilePanel, setShowProfilePanel] = useState(false);
  const [isProfileEditing, setIsProfileEditing] = useState(false);
  const [profileTab, setProfileTab] = useState("overview");
  const [myReviews, setMyReviews] = useState([]);
  const [billing, setBilling] = useState(null);

  const [theme, setTheme] = useState(() => localStorage.getItem("app-theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    if (!document.startViewTransition) {
      setTheme((prev) => (prev === "dark" ? "light" : "dark"));
      return;
    }

    document.startViewTransition(() => {
      setTheme((prev) => (prev === "dark" ? "light" : "dark"));
    });
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

  useEffect(() => {
    if (!showProfilePanel) return;

    const handleClickOutside = (e) => {
      if (profilePanelRef.current && !profilePanelRef.current.contains(e.target)) {
        setShowProfilePanel(false);
        setIsProfileEditing(false);
      }
    };

    const timerId = setTimeout(() => {
      document.addEventListener("mousedown", handleClickOutside);
    }, 100);

    return () => {
      clearTimeout(timerId);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showProfilePanel]);

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch {}
    clearAccessToken();
    localStorage.removeItem("currentUser");
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

  useEffect(() => {
    if (!showProfilePanel || !userId) return;

    (async () => {
      try {
        const resp = await fetchUserProfile(userId);
        setMyReviews(resp.data.reviews || []);
      } catch {}
      try {
        const billingResp = await fetchMyBilling();
        setBilling(billingResp.data || null);
      } catch {}
    })();
  }, [showProfilePanel, userId]);

  const avgRating = myReviews.length
    ? (myReviews.reduce((s, r) => s + r.rating, 0) / myReviews.length).toFixed(1)
    : currentUser.trust_score || 0;

  const renderStars = (score) => {
    const full = Math.round(Number(score));
    return Array.from({ length: 5 }, (_, i) => (
      <span key={i} style={{ color: i < full ? "#fbbf24" : "var(--border)", fontSize: 15 }}>*</span>
    ));
  };

  const roleLabel = {
    sponsor: "Company",
    organizer: "Organization",
    influencer: "Organization",
  }[role] || "Company";

  const roleValue = role === "sponsor" ? profile.companyName || "-" : profile.organizationName || "-";
  const planName = billing?.plan_tier ? String(billing.plan_tier).toUpperCase() : String(currentUser.plan_tier || "FREE").toUpperCase();

  return (
    <div className="navbar">
      <div className="navbar-left">
        <div
          className="brand-wrap"
          onClick={() => {
            if (role === "sponsor") navigate("/sponsor-dashboard");
            else if (role === "organizer") navigate("/organizer-dashboard");
            else navigate("/influencer-dashboard");
          }}
          style={{ cursor: "pointer" }}
        >
          <div className="brand-logo" aria-hidden="true">SH</div>
          <h2>Sponsorship Hub</h2>
        </div>
      </div>

      <div className="navbar-center">
        <span className="navbar-role-chip">
          <span className="role-dot" />
          {role === "sponsor"
            ? "Sponsor Console"
            : role === "organizer"
              ? "Organizer Command Center"
              : "Influencer Studio"}
        </span>
      </div>

      <div className="navbar-right">
        <NotificationBell />

        <div className="profile-wrap" ref={profilePanelRef}>
          <button
            className="profile-btn"
            onClick={() => {
              setShowProfilePanel(!showProfilePanel);
              setIsProfileEditing(false);
              setProfileTab("overview");
            }}
          >
            <span className="user-icon">{(profile.fullName || "U").charAt(0).toUpperCase()}</span>
            <span className="profile-btn-label">{profile.fullName || "Profile"}</span>
          </button>

          {showProfilePanel && (
            <div className="profile-popover">
              {!isProfileEditing ? (
                <>
                  <div className="popover-header">
                    <div>
                      <h4>My Profile</h4>
                      <p className="popover-subtitle">Manage your profile and trust details.</p>
                    </div>
                    <button type="button" className="edit-icon-btn" onClick={() => setIsProfileEditing(true)}>
                      Edit
                    </button>
                  </div>

                  <div className="profile-tabs">
                    <button
                      type="button"
                      className={`profile-tab-btn ${profileTab === "overview" ? "active" : ""}`}
                      onClick={() => setProfileTab("overview")}
                    >
                      Profile
                    </button>
                    <button
                      type="button"
                      className={`profile-tab-btn ${profileTab === "reviews" ? "active" : ""}`}
                      onClick={() => setProfileTab("reviews")}
                    >
                      Reviews ({myReviews.length})
                    </button>
                  </div>

                  {profileTab === "overview" ? (
                    <>
                      <div className="profile-info-grid">
                        <p><strong>Name:</strong> {profile.fullName || "-"}</p>
                        <p><strong>Email:</strong> {profile.email || "-"}</p>
                        <p><strong>Plan:</strong> {planName}</p>
                        <p><strong>Phone:</strong> {profile.phone || "-"}</p>
                        <p><strong>{roleLabel}:</strong> {roleValue}</p>
                        <p><strong>Location:</strong> {profile.city || profile.state ? `${profile.city}, ${profile.state}` : "-"}</p>
                      </div>

                      <div className="profile-review-list compact">
                        <h5>Trust Score</h5>
                        <div className="trust-score-row">
                          <div className="trust-stars-mini">{renderStars(avgRating)}</div>
                          <span className="trust-score-num">{Number(avgRating).toFixed(1)} / 5.0</span>
                          <span className="trust-review-count">({myReviews.length} review{myReviews.length !== 1 ? "s" : ""})</span>
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="profile-review-list">
                      <h5>Trust Score and Feedback</h5>
                      <div className="trust-score-row">
                        <div className="trust-stars-mini">{renderStars(avgRating)}</div>
                        <span className="trust-score-num">{Number(avgRating).toFixed(1)} / 5.0</span>
                        <span className="trust-review-count">({myReviews.length} review{myReviews.length !== 1 ? "s" : ""})</span>
                      </div>

                      {myReviews.length === 0 ? (
                        <p className="no-reviews">No reviews received yet.</p>
                      ) : (
                        myReviews.slice(0, 5).map((review) => (
                          <div key={review.id} className="profile-review-item">
                            <div className="review-item-top">
                              <span className="review-item-stars">
                                {Array.from({ length: 5 }, (_, i) => (
                                  <span key={i} style={{ color: i < review.rating ? "#fbbf24" : "rgba(255,255,255,0.15)", fontSize: 12 }}>*</span>
                                ))}
                              </span>
                              <span className="review-item-by">{review.reviewer_name}</span>
                            </div>
                            {review.comment && <p className="review-item-comment">"{review.comment}"</p>}
                          </div>
                        ))
                      )}

                      <button type="button" className="profile-ghost-btn" onClick={() => navigate(`/profile/${userId}`)}>
                        Open Full Public Profile
                      </button>
                    </div>
                  )}

                  <button type="button" className="profile-inline-btn" onClick={() => setIsProfileEditing(true)}>
                    Modify Profile
                  </button>
                </>
              ) : (
                <form onSubmit={handleSaveProfile} className="profile-edit-form">
                  <div className="popover-header edit">
                    <div>
                      <h4>Edit Profile</h4>
                      <p className="popover-subtitle">Update details visible in your account.</p>
                    </div>
                  </div>

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
                      {INDIAN_STATES.filter((s) => s !== "All States").map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>

                    <label>City</label>
                    <input type="text" name="city" value={profileForm.city} onChange={handleProfileChange} />
                    <label>About</label>
                    <textarea name="about" value={profileForm.about} onChange={handleProfileChange} rows="3" />
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

        <button className="theme-toggle-btn" onClick={toggleTheme} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>
          <div className="icon-wrapper">
            <span className="sun">☀</span>
            <span className="moon">☾</span>
          </div>
        </button>
      </div>
    </div>
  );
};

export default Navbar;
