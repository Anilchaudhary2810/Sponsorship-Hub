import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifyEmailToken } from "../services/api";
import "./VerifyEmail.css";

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const token = useMemo(() => searchParams.get("token") || "", [searchParams]);
  const [status, setStatus] = useState("loading");
  const [message, setMessage] = useState("Verifying your email...");

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

  return (
    <main className="verify-email-page">
      <section className="verify-email-card">
        <h1>Email Verification</h1>
        <p className={`verify-email-message ${status}`}>{message}</p>
        <div className="verify-email-actions">
          <Link to="/login" className="primary-link">Go to Login</Link>
          <Link to="/register" className="ghost-link">Back to Register</Link>
        </div>
      </section>
    </main>
  );
};

export default VerifyEmail;
