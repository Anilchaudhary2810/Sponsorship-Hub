import React, { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import {
  updateUser,
  fetchUserProfile,
  fetchMyBilling,
  fetchTrustProfile,
  submitKyc,
} from "../services/api";
import { INDIAN_STATES } from "../utils/constants";
import "./MyProfilePage.css";

const MyProfilePage = () => {
  const currentUser = useMemo(() => JSON.parse(localStorage.getItem("currentUser") || "{}"), []);
  const role = currentUser.role || "sponsor";
  const userId = currentUser.id;

  const [activeTab, setActiveTab] = useState("overview");
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [kycSubmitting, setKycSubmitting] = useState(false);

  const [myReviews, setMyReviews] = useState([]);
  const [billing, setBilling] = useState(null);
  const [trustProfile, setTrustProfile] = useState(null);

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
  const [kycForm, setKycForm] = useState({
    document_type: "aadhaar",
    document_number_masked: "",
    document_url: "",
  });

  useEffect(() => {
    if (!userId) return;
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
  }, [userId]);

  const avgRating = myReviews.length
    ? (myReviews.reduce((s, r) => s + r.rating, 0) / myReviews.length).toFixed(1)
    : String(currentUser.trust_score || "0");

  const roleLabel = role === "sponsor" ? "Company" : "Organization";
  const roleValue = role === "sponsor" ? profile.companyName || "-" : profile.organizationName || "-";
  const planName = billing?.plan_tier
    ? String(billing.plan_tier).toUpperCase()
    : String(currentUser.plan_tier || "FREE").toUpperCase();

  const handleProfileChange = (e) => {
    setProfileForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    if (!userId) return;
    setSaving(true);
    const payload = {
      full_name: profileForm.fullName || null,
      phone: profileForm.phone || null,
      state: profileForm.state || null,
      city: profileForm.city || null,
      about: profileForm.about || null,
    };

    if (role === "sponsor") payload.company_name = profileForm.companyName || null;
    else payload.organization_name = profileForm.organizationName || null;

    try {
      const resp = await updateUser(userId, payload);
      const updatedUser = resp.data;
      localStorage.setItem("currentUser", JSON.stringify(updatedUser));
      const updated = {
        fullName: updatedUser.full_name || "",
        email: updatedUser.email || "",
        phone: updatedUser.phone || "",
        companyName: updatedUser.company_name || "",
        organizationName: updatedUser.organization_name || "",
        state: updatedUser.state || "",
        city: updatedUser.city || "",
        about: updatedUser.about || "",
      };
      setProfile(updated);
      setProfileForm(updated);
      setIsEditing(false);
      toast.success("Profile updated");
    } catch {
      toast.error("Unable to save profile");
    } finally {
      setSaving(false);
    }
  };

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
      setKycForm((prev) => ({ ...prev, document_number_masked: "", document_url: "" }));
      toast.success("KYC submitted");
    } catch (err) {
      const msg = err?.response?.data?.message || err?.response?.data?.detail || "KYC submission failed";
      toast.error(msg);
    } finally {
      setKycSubmitting(false);
    }
  };

  return (
    <div>
      <Navbar role={role} />
      <main className="my-profile-page">
        <header className="my-profile-header">
          <h1>My Profile</h1>
          <p>Manage account, trust, KYC, and public profile details from one place.</p>
        </header>

        <div className="my-profile-tabs">
          <button className={activeTab === "overview" ? "active" : ""} onClick={() => { setActiveTab("overview"); setIsEditing(false); }}>
            Overview
          </button>
          <button className={activeTab === "edit" ? "active" : ""} onClick={() => { setActiveTab("edit"); setIsEditing(true); }}>
            Edit Profile
          </button>
          <button className={activeTab === "reviews" ? "active" : ""} onClick={() => { setActiveTab("reviews"); setIsEditing(false); }}>
            Reviews
          </button>
          <button className={activeTab === "trust" ? "active" : ""} onClick={() => { setActiveTab("trust"); setIsEditing(false); }}>
            Trust and KYC
          </button>
        </div>

        {activeTab === "overview" && (
          <section className="my-profile-card">
            <div className="profile-grid">
              <p><strong>Name:</strong> {profile.fullName || "-"}</p>
              <p><strong>Email:</strong> {profile.email || "-"}</p>
              <p><strong>Plan:</strong> {planName}</p>
              <p><strong>Phone:</strong> {profile.phone || "-"}</p>
              <p><strong>{roleLabel}:</strong> {roleValue}</p>
              <p><strong>Location:</strong> {profile.city || profile.state ? `${profile.city}, ${profile.state}` : "-"}</p>
              <p><strong>About:</strong> {profile.about || "-"}</p>
              <p><strong>Trust Score:</strong> {Number(avgRating).toFixed(1)} / 5.0</p>
            </div>
          </section>
        )}

        {activeTab === "edit" && (
          <section className="my-profile-card">
            <form onSubmit={handleSaveProfile} className="my-profile-form">
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
              <textarea name="about" rows="4" value={profileForm.about} onChange={handleProfileChange} />

              <div className="my-profile-actions">
                <button type="button" className="ghost" onClick={() => setProfileForm(profile)}>Reset</button>
                <button type="submit" disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button>
              </div>
            </form>
          </section>
        )}

        {activeTab === "reviews" && (
          <section className="my-profile-card">
            <h3>My Reviews ({myReviews.length})</h3>
            {myReviews.length === 0 ? (
              <p className="muted">No reviews received yet.</p>
            ) : (
              <div className="review-list">
                {myReviews.map((review) => (
                  <article key={review.id} className="review-item">
                    <div className="review-top">
                      <strong>{review.reviewer_name || "Reviewer"}</strong>
                      <span>{review.rating}/5</span>
                    </div>
                    {review.comment ? <p>{review.comment}</p> : <p className="muted">No written feedback.</p>}
                  </article>
                ))}
              </div>
            )}
          </section>
        )}

        {activeTab === "trust" && (
          <section className="my-profile-card">
            <div className="trust-row">
              <span className={`kyc-chip ${trustProfile?.kyc_status || "not_submitted"}`}>
                KYC: {(trustProfile?.kyc_status || "not_submitted").replace("_", " ")}
              </span>
              <span className={`risk-chip ${trustProfile?.risk_level || "low"}`}>
                Risk: {trustProfile?.risk_level || "low"}
              </span>
            </div>
            <p className="muted">
              Risk flags: {(trustProfile?.risk_flags || []).length ? trustProfile.risk_flags.join(", ") : "none"}
            </p>

            <form onSubmit={handleSubmitKyc} className="my-profile-form">
              <label>Document Type</label>
              <select name="document_type" value={kycForm.document_type} onChange={handleKycInput}>
                <option value="aadhaar">Aadhaar</option>
                <option value="pan">PAN</option>
                <option value="passport">Passport</option>
                <option value="gst">GST</option>
                <option value="other">Other</option>
              </select>

              <label>Masked Document Number</label>
              <input
                type="text"
                name="document_number_masked"
                value={kycForm.document_number_masked}
                onChange={handleKycInput}
                placeholder="XXXX-XXXX-1234"
              />

              <label>Document URL (optional)</label>
              <input
                type="text"
                name="document_url"
                value={kycForm.document_url}
                onChange={handleKycInput}
                placeholder="https://..."
              />

              <div className="my-profile-actions">
                <button type="submit" disabled={kycSubmitting}>{kycSubmitting ? "Submitting..." : "Submit KYC"}</button>
              </div>
            </form>
          </section>
        )}
      </main>
    </div>
  );
};

export default MyProfilePage;
