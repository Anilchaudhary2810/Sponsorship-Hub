import React, { useState } from "react";
import "./AgreementModal.css";

const AgreementModal = ({ deal, role, onSign, onClose }) => {
  const [signature, setSignature] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [signed, setSigned] = useState(false);

  // prefill if already signed
  React.useEffect(() => {
    if (deal) {
      const existing = role === "organizer" ? deal.organizerSignature : deal.sponsorSignature;
      if (existing) {
        setSignature(existing);
        setSigned(true);
      }
    }
  }, [deal, role]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    // simulate confirmation animation
    setTimeout(() => {
      setSigned(true);
      if (onSign) onSign(signature);
    }, 500);
  };

  return (
    <div className="agreement-modal-overlay" onClick={onClose}>
      <div
        className="agreement-modal-content"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="agreement-modal-close"
          onClick={onClose}
          aria-label="Close agreement modal"
        >
          ×
        </button>
        <h2>Agreement</h2>
        <p className="agreement-role">Role: {role}</p>
        <div className="agreement-text-container">
          <div className="agreement-text">
            {deal && deal.content ? deal.content : "No agreement text provided."}
          </div>
        </div>
        {!signed ? (
          <form className="agreement-form" onSubmit={handleSubmit}>
            <label>
              Digital Signature (full name)
              <input
                type="text"
                value={signature}
                onChange={(e) => setSignature(e.target.value)}
                required
              />
            </label>
            <button type="submit" disabled={submitting || !signature} className="sign-button">
              {submitting ? "Signing..." : "Sign"}
            </button>
          </form>
        ) : (
          <div className="signed-confirmation">
            <span className="checkmark">✓</span>
            <p>Agreement signed!</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgreementModal;
