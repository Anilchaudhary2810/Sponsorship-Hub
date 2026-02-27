import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import { registerUser } from "../services/api";
import "./Register.css";

const Register = () => {
  const navigate = useNavigate();
  const [role, setRole] = useState("sponsor");
  const [isFlipping, setIsFlipping] = useState(false);
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "",
    confirmPassword: "",
    company_name: "",
    organization_name: "",
    instagram_handle: "",
    youtube_channel: "",
    audience_size: "",
    niche: "",
  });
  const [showPassword, setShowPassword] = useState(false);

  const handleRoleChange = (newRole) => {
    setIsFlipping(true);
    setRole(newRole);
    setTimeout(() => setIsFlipping(false), 600);
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!role) {
      toast.error("Please select a role");
      return;
    }
    if (formData.password !== formData.confirmPassword) {
      toast.error("Passwords do not match");
      return;
    }

    try {
      const payload = {
        full_name: formData.full_name,
        email: formData.email,
        phone: formData.phone,
        password: formData.password,
        role,
        // Only send fields relevant to the role to ensure "perfect match" with backend logic
        company_name: role === "sponsor" ? formData.company_name : null,
        organization_name: role === "organizer" ? formData.organization_name : null,
        instagram_handle: role === "influencer" ? formData.instagram_handle : null,
        niche: role === "influencer" ? formData.niche : null,
        audience_size: role === "influencer" ? (parseInt(formData.audience_size) || 0) : 0,
        // Common optional fields initialized to null if not present
        youtube_channel: null,
      };
      
      console.log("Registering with payload:", payload);
      const resp = await registerUser(payload);
      const { access_token, user } = resp.data;
      
      localStorage.setItem("authToken", access_token);
      localStorage.setItem("currentUser", JSON.stringify(user));
      toast.success("Registration successful! Welcome aboard 🎉");
      
      if (user.role === "sponsor") navigate("/sponsor-dashboard");
      else if (user.role === "organizer") navigate("/organizer-dashboard");
      else navigate("/influencer-dashboard");
    } catch (err) {
      console.error("Registration error:", err);
      // Show fallback message if the interceptor didn't already toast
      if (!err.response) {
        toast.error("Cannot reach server. Is the backend running?");
      }
    }
  };

  return (
    <div className="register-container">
      <div className="register-card">
        <h2 className="register-title">Register</h2>

        <form onSubmit={handleSubmit}>
          <div className="role-container">
            <label>
              <input type="radio" value="sponsor" checked={role === "sponsor"} onChange={(e) => handleRoleChange(e.target.value)} />
              Sponsor
            </label>
            <label>
              <input type="radio" value="organizer" checked={role === "organizer"} onChange={(e) => handleRoleChange(e.target.value)} />
              Organizer
            </label>
            <label>
              <input type="radio" value="influencer" checked={role === "influencer"} onChange={(e) => handleRoleChange(e.target.value)} />
              Influencer
            </label>
          </div>

          <div className={`register-cols ${isFlipping ? "page-flip" : ""}`}>
            <input type="text" name="full_name" placeholder="Full Name" required value={formData.full_name} onChange={handleChange} className="register-input" autoComplete="name" />
            
            {role === "sponsor" && (
              <input type="text" name="company_name" placeholder="Company Name" required value={formData.company_name} onChange={handleChange} className="register-input" />
            )}
            {role === "organizer" && (
              <input type="text" name="organization_name" placeholder="Organization Name" required value={formData.organization_name} onChange={handleChange} className="register-input" />
            )}
            {role === "influencer" && (
              <input type="text" name="instagram_handle" placeholder="Instagram @handle" required value={formData.instagram_handle} onChange={handleChange} className="register-input" />
            )}

            <input type="email" name="email" placeholder="Email" required value={formData.email} onChange={handleChange} className="register-input" autoComplete="email" />
            <input type="text" name="phone" placeholder="Phone" required value={formData.phone} onChange={handleChange} className="register-input" autoComplete="tel" />

            {role === "influencer" && (
              <>
                <input type="text" name="niche" placeholder="Niche (e.g. Comedy, Tech)" required value={formData.niche} onChange={handleChange} className="register-input" />
                <input type="number" name="audience_size" placeholder="Total Audience (e.g. 50000)" required value={formData.audience_size} onChange={handleChange} className="register-input" />
              </>
            )}

            <div className="password-input-wrapper">
              <input 
                type={showPassword ? "text" : "password"} 
                name="password" 
                placeholder="Password" 
                required 
                value={formData.password} 
                onChange={handleChange} 
                className="register-input" 
                autoComplete="new-password"
              />
              <span 
                className="password-toggle-icon" 
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? "👁️" : "👁️‍🗨️"}
              </span>
            </div>

            <div className="password-input-wrapper">
              <input 
                type={showPassword ? "text" : "password"} 
                name="confirmPassword" 
                placeholder="Confirm Password" 
                required 
                value={formData.confirmPassword} 
                onChange={handleChange} 
                className="register-input" 
                autoComplete="new-password"
              />
            </div>
          </div>

          <button type="submit" className="register-button">Register as {role || 'User'}</button>
          <p className="register-link">
            Already have an account? <span onClick={() => navigate("/login")}>Login</span>
          </p>
        </form>
      </div>
      <div className="register-decoration">
        <div className="glass-shape shape-1"></div>
        <div className="glass-shape shape-2"></div>
      </div>
    </div>
  );
};

export default Register;
