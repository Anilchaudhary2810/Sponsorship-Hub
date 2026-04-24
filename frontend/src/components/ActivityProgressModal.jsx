import React, { useEffect, useMemo, useState } from "react";
import "./ActivityProgressModal.css";

const getSubject = (deal) => {
  if (deal?.deal_type === "sponsorship") {
    return deal.event?.title || "Event partnership";
  }
  return deal.campaign?.title || "Campaign partnership";
};

const getPartnerName = (deal, role) => {
  if (role === "sponsor") {
    return deal?.deal_type === "sponsorship"
      ? deal.organizerName || "Organizer"
      : deal.influencerName || deal.influencer?.full_name || "Creator";
  }
  if (role === "organizer") return deal.sponsorName || "Sponsor";
  return deal.sponsorName || "Sponsor";
};

const getActorStatus = (deal, role) => {
  if (role === "sponsor") {
    return {
      currentAccepted: !!deal.sponsorAccepted,
      otherAccepted: deal.deal_type === "sponsorship" ? !!deal.organizerAccepted : !!deal.influencerAccepted,
      currentSigned: !!deal.sponsorSigned,
      otherSigned: deal.deal_type === "sponsorship" ? !!deal.organizerSigned : !!deal.influencerSigned,
    };
  }
  if (role === "organizer") {
    return {
      currentAccepted: !!deal.organizerAccepted,
      otherAccepted: !!deal.sponsorAccepted,
      currentSigned: !!deal.organizerSigned,
      otherSigned: !!deal.sponsorSigned,
    };
  }
  return {
    currentAccepted: !!deal.influencerAccepted,
    otherAccepted: !!deal.sponsorAccepted,
    currentSigned: !!deal.influencerSigned,
    otherSigned: !!deal.sponsorSigned,
  };
};

const buildSteps = (deal, role, isReviewed, actions) => {
  const status = getActorStatus(deal, role);
  const acceptedDone = status.currentAccepted && status.otherAccepted;
  const paymentDone = !!deal.paymentDone;
  const signedDone = status.currentSigned && status.otherSigned;
  const closedDone = deal.status === "closed";
  const reviewedDone = !!isReviewed;

  return [
    {
      key: "proposal",
      label: "Proposal Sent",
      done: true,
      helper: "Deal request created successfully.",
    },
    {
      key: "acceptance",
      label: "Acceptance",
      done: acceptedDone,
      helper: acceptedDone
        ? "Both sides accepted this deal."
        : status.currentAccepted
          ? "Waiting for the other side to accept."
          : "Your acceptance is required.",
      actionLabel: !status.currentAccepted && typeof actions.accept === "function" ? "Accept now" : null,
      action: !status.currentAccepted ? actions.accept : null,
    },
    {
      key: "payment",
      label: "Payment",
      done: paymentDone,
      helper: paymentDone
        ? "Payment has been completed."
        : role === "sponsor"
          ? "Sponsor payment is pending."
          : "Waiting for sponsor payment.",
      actionLabel: !paymentDone && role === "sponsor" && typeof actions.pay === "function" ? "Pay now" : null,
      action: !paymentDone && role === "sponsor" ? actions.pay : null,
    },
    {
      key: "sign",
      label: "Agreement Sign",
      done: signedDone,
      helper: signedDone
        ? "Both signatures are complete."
        : !paymentDone
          ? "Signing unlocks after payment."
          : status.currentSigned
            ? "Waiting for the other signature."
            : "Your signature is pending.",
      actionLabel: paymentDone && !status.currentSigned && typeof actions.sign === "function" ? "Sign now" : null,
      action: paymentDone && !status.currentSigned ? actions.sign : null,
    },
    {
      key: "close",
      label: "Closure",
      done: closedDone,
      helper: closedDone ? "Deal is closed." : "Deal has not reached close state yet.",
    },
    {
      key: "review",
      label: "Review",
      done: reviewedDone,
      helper: reviewedDone
        ? "Review already submitted."
        : closedDone
          ? "Submit your review to complete the flow."
          : "Review unlocks after closure.",
      actionLabel: closedDone && !reviewedDone && typeof actions.review === "function" ? "Review now" : null,
      action: closedDone && !reviewedDone ? actions.review : null,
    },
  ];
};

const ActivityProgressModal = ({
  deal,
  role,
  isReviewed = false,
  onClose,
  onOpenDetails,
  actions = {},
  formatCurrency,
}) => {
  const [animatedProgress, setAnimatedProgress] = useState(0);

  const steps = useMemo(
    () => (deal ? buildSteps(deal, role, isReviewed, actions) : []),
    [deal, role, isReviewed, actions]
  );

  const completedCount = steps.filter((step) => step.done).length;
  const progressPercent = steps.length ? Math.round((completedCount / steps.length) * 100) : 0;

  useEffect(() => {
    setAnimatedProgress(0);
    const timer = setTimeout(() => setAnimatedProgress(progressPercent), 50);
    return () => clearTimeout(timer);
  }, [progressPercent, deal?.id]);

  if (!deal) return null;

  const runAction = (handler) => {
    if (typeof handler !== "function") return;
    handler();
    if (typeof onClose === "function") onClose();
  };

  const amount = Number(deal.paymentAmount) || Number(deal.event?.budget) || Number(deal.campaign?.budget) || 0;
  const safeFormatCurrency = typeof formatCurrency === "function"
    ? formatCurrency
    : (value) => `INR ${Number(value || 0).toLocaleString("en-IN")}`;

  return (
    <div className="activity-progress-overlay" onClick={onClose}>
      <div className="activity-progress-card" onClick={(event) => event.stopPropagation()}>
        <button type="button" className="activity-progress-close" onClick={onClose} aria-label="Close progress modal">
          x
        </button>

        <p className="activity-progress-eyebrow">{deal.deal_type === "sponsorship" ? "Event Deal" : "Creator Deal"}</p>
        <h3 className="activity-progress-title">{getSubject(deal)}</h3>
        <p className="activity-progress-subtitle">Partner: {getPartnerName(deal, role)}</p>

        <div className="activity-progress-meta">
          <span className="activity-progress-chip">ID #{deal.id}</span>
          <span className="activity-progress-chip">Value: {safeFormatCurrency(amount)}</span>
          <span className="activity-progress-chip">Status: {(deal.status || "pending").replace("_", " ")}</span>
        </div>

        <div className="activity-progress-track-wrap">
          <div className="activity-progress-track">
            <div className="activity-progress-fill" style={{ width: `${animatedProgress}%` }} />
          </div>
          <span className="activity-progress-percent">{animatedProgress}% complete</span>
        </div>

        <div className="activity-progress-step-list">
          {steps.map((step) => (
            <div
              key={step.key}
              className={`activity-progress-step ${step.done ? "done" : "pending"}`}
            >
              <div className="activity-progress-step-main">
                <span className="activity-progress-step-label">{step.label}</span>
                <span className="activity-progress-step-helper">{step.helper}</span>
              </div>
              {step.actionLabel && (
                <button
                  type="button"
                  className="activity-progress-step-btn"
                  onClick={() => runAction(step.action)}
                >
                  {step.actionLabel}
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="activity-progress-footer-actions">
          {typeof onOpenDetails === "function" && (
            <button type="button" className="activity-progress-aux-btn" onClick={() => runAction(onOpenDetails)}>
              Open Details
            </button>
          )}
          {typeof actions.agreement === "function" && (
            <button type="button" className="activity-progress-aux-btn" onClick={() => runAction(actions.agreement)}>
              Agreement
            </button>
          )}
          {typeof actions.invoice === "function" && (
            <button type="button" className="activity-progress-aux-btn" onClick={() => runAction(actions.invoice)}>
              Invoice
            </button>
          )}
          {typeof actions.chat === "function" && (
            <button type="button" className="activity-progress-aux-btn primary" onClick={() => runAction(actions.chat)}>
              Chat
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ActivityProgressModal;
