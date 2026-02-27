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
    try {
      console.log("Attempting login for:", formData.email);
      const resp = await loginUser(formData);
      const { access_token, user } = resp.data;
      
      localStorage.setItem("authToken", access_token);
      localStorage.setItem("currentUser", JSON.stringify(user));
      
      toast.success(`Welcome back, ${user.full_name}!`);

      if (user.role === "sponsor") navigate("/sponsor-dashboard");
      else if (user.role === "organizer") navigate("/organizer-dashboard");
      else if (user.role === "influencer") navigate("/influencer-dashboard");
      else navigate("/login");
    } catch (err) {
      console.error("Login error:", err);
      // Show fallback message if the interceptor didn't already toast
      if (!err.response) {
        toast.error("Cannot reach server. Is the backend running?");
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">SS</div>
          <h2 className="login-title">Sign In</h2>
          <p className="login-subtitle">Continue to your Sponsorship Hub</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
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
