import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import "./Navbar.css";
import { updateUser, fetchUserProfile, fetchMyBilling, logoutUser, fetchTrustProfile, submitKyc } from "../services/api";
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
  const [trustProfile, setTrustProfile] = useState(null);
  const [kycSubmitting, setKycSubmitting] = useState(false);
  const [kycForm, setKycForm] = useState({
    document_type: "aadhaar",
    document_number_masked: "",
    document_url: "",
  });

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
  const logoutWrapRef = useRef(null);

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

  useEffect(() => {
    if (!showLogoutConfirm) return;

    const handleClickOutside = (e) => {
      if (logoutWrapRef.current && !logoutWrapRef.current.contains(e.target)) {
        setShowLogoutConfirm(false);
      }
    };

    const timerId = setTimeout(() => {
      document.addEventListener("mousedown", handleClickOutside);
    }, 60);

    return () => {
      clearTimeout(timerId);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showLogoutConfirm]);

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch {}
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
      try {
        const trustResp = await fetchTrustProfile();
        setTrustProfile(trustResp.data || null);
      } catch {}
    })();
  }, [showProfilePanel, userId]);

  const handleKycInput = (e) => {
    setKycForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmitKyc = async (e) => {
    e.preventDefault();
    if (!kycForm.document_number_masked.trim()) {
      toast.error("Enter masked document number");
      return;
    }
    setKycSubmitting(true);
    try {
      await submitKyc({
        document_type: kycForm.document_type,
        document_number_masked: kycForm.document_number_masked.trim(),
        document_url: kycForm.document_url.trim() || null,
      });
      const trustResp = await fetchTrustProfile();
      setTrustProfile(trustResp.data || null);
      toast.success("KYC submitted for review");
      setKycForm((prev) => ({ ...prev, document_number_masked: "", document_url: "" }));
    } catch (err) {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || "KYC submission failed";
      toast.error(msg);
    } finally {
      setKycSubmitting(false);
    }
  };

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
            onClick={() => navigate("/my-profile")}
          >
            <span className="user-icon">{(profile.fullName || "U").charAt(0).toUpperCase()}</span>
            <span className="profile-btn-label">{profile.fullName || "Profile"}</span>
          </button>
        </div>

        <div className="logout-wrap" ref={logoutWrapRef}>
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
