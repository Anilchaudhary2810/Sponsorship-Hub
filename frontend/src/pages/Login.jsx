import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { loginUser } from "../services/api";
import SplashScreen from "./SplashScreen";
import "./Login.css";

let appHasLoaded = false;

const Login = () => {
  const navigate = useNavigate();
  const [showSplash, setShowSplash] = useState(!appHasLoaded);

  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  React.useEffect(() => {
    if (!appHasLoaded) {
      appHasLoaded = true;
    }
  }, []);

  // Use a second effect to check for existing login and redirect
  // This handles the "landing on /login when already authed" case
  React.useEffect(() => {
    const user = JSON.parse(localStorage.getItem("currentUser") || "null");
    if (user) {
      const role = user.role?.toLowerCase();
      if (role === "sponsor") navigate("/sponsor-dashboard");
      else if (role === "organizer") navigate("/organizer-dashboard");
      else if (role === "influencer") navigate("/influencer-dashboard");
      else if (role === "admin") navigate("/scale-ops?tab=admin");
      // If valid role not found, we just stay at login
    }
  }, [navigate]);

  if (showSplash) {
    return <SplashScreen onComplete={() => setShowSplash(false)} />;
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Basic Client-side validation
    if (!formData.email || !formData.password) {
      toast.error("Please fill in all fields");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      toast.error("Please enter a valid email address");
      return;
    }

    try {
      const resp = await loginUser(formData);
      const { user } = resp.data;
      localStorage.setItem("currentUser", JSON.stringify(user));
      
      toast.success(`Welcome back, ${user.full_name}!`);

      const role = user.role?.toLowerCase();
      if (role === "sponsor") navigate("/sponsor-dashboard");
      else if (role === "organizer") navigate("/organizer-dashboard");
      else if (role === "influencer") navigate("/influencer-dashboard");
      else if (role === "admin") navigate("/scale-ops?tab=admin");
      else navigate("/login");
    } catch (err) {
      console.warn("Login request failed", {
        status: err?.response?.status ?? null,
        code: err?.code ?? null,
      });
      
      if (err.response) {
        // The server responded with a status code outside the 2xx range
        const message = err.response.data?.detail || err.response.data?.message || "Invalid credentials or account issue";
        toast.error(message);
      } else if (err.request) {
        // The request was made but no response was received
        toast.error("No response from server. Check your connection.");
      } else {
        // Something happened in setting up the request
        toast.error("Failed to send login request");
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">SH</div>
          <h2 className="login-title">Sign In</h2>
          <p className="login-subtitle">Continue to your Sponsorship Hub</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form" noValidate>
          <div className="input-group">
            <label htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              name="email"
              value={formData.email}
              placeholder="name@company.com"
              required
              onChange={handleChange}
              className="login-input"
              autoComplete="email"
            />
          </div>

          <div className="input-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              name="password"
              value={formData.password}
              placeholder="••••••••"
              required
              onChange={handleChange}
              className="login-input"
              autoComplete="current-password"
            />
            <div className="forgot-password-link-container">
              <span className="forgot-password-link" onClick={() => navigate("/forgot-password")}>
                Forgot Password?
              </span>
            </div>
          </div>

          <button type="submit" className="login-button">
            Login to Dashboard
          </button>
        </form>

        <div className="login-footer">
          <p>
            Don't have an account?{" "}
            <span className="register-link-span" onClick={() => navigate("/register")}>
              Create one for free
            </span>
          </p>
          <p style={{ marginTop: '0.5rem' }}>
            <span className="register-link-span" style={{ fontSize: '0.8rem', opacity: 0.7 }} onClick={() => navigate("/")}>
              Back to Homepage
            </span>
          </p>
        </div>
      </div>
      
      <div className="login-decoration">
        <div className="glass-shape shape-1"></div>
        <div className="glass-shape shape-2"></div>
      </div>
    </div>
  );
};

export default Login;
