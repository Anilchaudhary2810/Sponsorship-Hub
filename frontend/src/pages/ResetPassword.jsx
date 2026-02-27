import React, { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import { resetPassword } from "../services/api";
import "./Login.css";

const ResetPassword = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      return toast.error("Passwords do not match");
    }
    if (!token) {
      return toast.error("No reset token found in URL");
    }

    setIsLoading(true);
    try {
      await resetPassword({ token, new_password: password });
      toast.success("Password reset successfully! Redirecting to login...");
      setTimeout(() => navigate("/login"), 2000);
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
          <h2 className="login-title">New Password</h2>
          <p className="login-subtitle">Enter your new secure password</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label>New Password</label>
            <input
              type="password"
              value={password}
              placeholder="••••••••"
              required
              onChange={(e) => setPassword(e.target.value)}
              className="login-input"
            />
          </div>

          <div className="input-group">
            <label>Confirm Password</label>
            <input
              type="password"
              value={confirmPassword}
              placeholder="••••••••"
              required
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="login-input"
            />
          </div>

          <button type="submit" className="login-button" disabled={isLoading}>
            {isLoading ? "Saving..." : "Update Password"}
          </button>
        </form>
      </div>
      
      <div className="login-decoration">
        <div className="glass-shape shape-1"></div>
        <div className="glass-shape shape-2"></div>
      </div>
    </div>
  );
};

export default ResetPassword;
