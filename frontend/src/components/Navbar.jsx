import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Navbar.css";
import { logoutUser } from "../services/api";
import NotificationBell from "./NotificationBell";

const getStoredUser = () => {
  try {
    const raw = localStorage.getItem("currentUser");
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const Navbar = ({ role }) => {
  const navigate = useNavigate();
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const [theme, setTheme] = useState(() => localStorage.getItem("app-theme") || "dark");
  const logoutWrapRef = useRef(null);

  const currentUser = getStoredUser();
  const isAdmin = String(currentUser.role || role || "").toLowerCase() === "admin";
  const displayName = currentUser.full_name || currentUser.name || "Profile";

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  useEffect(() => {
    if (!showLogoutConfirm) return;

    const handleClickOutside = (event) => {
      if (logoutWrapRef.current && !logoutWrapRef.current.contains(event.target)) {
        setShowLogoutConfirm(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showLogoutConfirm]);

  const toggleTheme = () => {
    if (!document.startViewTransition) {
      setTheme((prev) => (prev === "dark" ? "light" : "dark"));
      return;
    }

    document.startViewTransition(() => {
      setTheme((prev) => (prev === "dark" ? "light" : "dark"));
    });
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch (err) {
      // Logout can fail if session is already expired; continue local sign-out.
      console.warn("[Navbar] logout request failed", err);
    }
    localStorage.removeItem("currentUser");
    navigate("/login");
  };

  return (
    <div className="navbar">
      <div className="navbar-left">
        <div
          className="brand-wrap"
          onClick={() => {
            if (role === "sponsor") navigate("/sponsor-dashboard");
            else if (role === "organizer") navigate("/organizer-dashboard");
            else if (role === "admin") navigate("/admin");
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
              : role === "admin"
                ? "Admin Operations"
                : "Influencer Studio"}
        </span>
      </div>

      <div className="navbar-right">
        <button
          type="button"
          className="admin-nav-btn"
          onClick={() => navigate(isAdmin ? "/admin" : "/scale-ops")}
        >
          {isAdmin ? "Admin Panel" : "Scale Ops"}
        </button>

        <NotificationBell />

        <div className="profile-wrap">
          <button
            className="profile-btn"
            onClick={() => navigate("/my-profile")}
          >
            <span className="user-icon">{displayName.charAt(0).toUpperCase()}</span>
            <span className="profile-btn-label">{displayName}</span>
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
                <button type="button" className="logout-cancel-btn" onClick={() => setShowLogoutConfirm(false)}>
                  Stay
                </button>
                <button type="button" className="logout-confirm-btn" onClick={handleLogout}>
                  Logout
                </button>
              </div>
            </div>
          )}
        </div>

        <button className="theme-toggle-btn" onClick={toggleTheme} title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}>
          <div className="icon-wrapper">
            <span className="sun">&#9728;</span>
            <span className="moon">&#9790;</span>
          </div>
        </button>
      </div>
    </div>
  );
};

export default Navbar;
