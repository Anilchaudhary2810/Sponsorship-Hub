import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resendVerificationEmail, verifyEmailToken } from "../services/api";
import "./VerifyEmail.css";

const VerifyEmail = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get("token") || "", [searchParams]);
  const emailFromQuery = useMemo(() => searchParams.get("email") || "", [searchParams]);
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("Verifying your email...");
  const [resendEmail, setResendEmail] = useState(emailFromQuery);
  const [resendStatus, setResendStatus] = useState("idle");
  const [resendMessage, setResendMessage] = useState("");

  useEffect(() => {
    setResendEmail(emailFromQuery);
  }, [emailFromQuery]);

  useEffect(() => {
    let isMounted = true;

    const run = async () => {
      if (!token) {
        if (isMounted) {
          setStatus("error");
          setMessage("Verification token is missing.");
        }
        return;
      }

      try {
        const resp = await verifyEmailToken(token);
        if (!isMounted) return;
        setStatus("success");
        setMessage(resp.data?.message || "Email verified successfully.");
      } catch (err) {
        if (!isMounted) return;
        const apiMsg = err?.response?.data?.message || err?.response?.data?.detail;
        setStatus("error");
        setMessage(apiMsg || "Verification failed. The link may be invalid or expired.");
      }
    };

    run();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const handleResend = async (e) => {
    e.preventDefault();
    const normalizedEmail = resendEmail.trim();
    if (!normalizedEmail) {
      setResendStatus("error");
      setResendMessage("Please enter your email address.");
      return;
    }

    setResendStatus("loading");
    setResendMessage("");
    try {
      const resp = await resendVerificationEmail({ email: normalizedEmail });
      setResendStatus("sent");
      setResendMessage(resp.data?.message || "Verification email sent.");

      const previewToken = resp.data?.verification_token_preview;
      if (previewToken) {
        setStatus("loading");
        setMessage("Verifying your new email token...");
        navigate(`/verify-email?token=${encodeURIComponent(previewToken)}&email=${encodeURIComponent(normalizedEmail)}`, {
          replace: true,
        });
      }
    } catch (err) {
      const apiMsg = err?.response?.data?.message || err?.response?.data?.detail;
      setResendStatus("error");
      setResendMessage(apiMsg || "Unable to resend verification email.");
    }
  };

  return (
    <main className="verify-email-page">
      <section className="verify-email-card">
        <h1>Email Verification</h1>
        <p className={`verify-email-message ${status}`}>{message}</p>
        {(status === "error" || !token) && (
          <div className="verify-email-resend">
            <p className="verify-email-help">Need a fresh link? Enter your email to resend verification.</p>
            <form onSubmit={handleResend} className="verify-email-form">
              <input
                type="email"
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
                placeholder="you@example.com"
                className="verify-email-input"
                autoComplete="email"
                required
              />
              <button
                type="submit"
                className="verify-email-resend-btn"
                disabled={resendStatus === "loading"}
              >
                {resendStatus === "loading" ? "Sending..." : "Resend Verification Email"}
              </button>
            </form>
            {resendMessage ? (
              <p className={`verify-email-resend-message ${resendStatus === "error" ? "error" : "success"}`}>
                {resendMessage}
              </p>
            ) : null}
          </div>
        )}
        <div className="verify-email-actions">
          <Link to="/login" className="primary-link">Go to Login</Link>
          <Link to="/register" className="ghost-link">Back to Register</Link>
        </div>
      </section>
    </main>
  );
};

export default VerifyEmail;
