import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { forgotPassword } from "../services/api";
import "./Login.css"; // Reuse the same premium styling base

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await forgotPassword({ email });
      toast.success("Reset link sent! Please check your inbox (or console for demo).");
      setTimeout(() => navigate("/login"), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">SS</div>
          <h2 className="login-title">Reset Password</h2>
          <p className="login-subtitle">We'll send you a recovery link</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label>Registered Email</label>
            <input
              type="email"
              value={email}
              placeholder="name@company.com"
              required
              onChange={(e) => setEmail(e.target.value)}
              className="login-input"
            />
          </div>

          <button type="submit" className="login-button" disabled={isLoading}>
            {isLoading ? "Sending..." : "Send Reset Link"}
          </button>
        </form>

        <div className="login-footer">
          <p>
            Remember your password?{" "}
            <span className="register-link-span" onClick={() => navigate("/login")}>
              Back to Sign In
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

export default ForgotPassword;
