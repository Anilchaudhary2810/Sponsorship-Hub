import React from "react";
import "./DealProgress.css";

const steps = [
  { key: "requested", label: "Requested" },
  { key: "agreed", label: "Agreed" },
  { key: "payment", label: "Payment" },
  { key: "signed", label: "Signed" },
  { key: "closed", label: "Closed" },
];

const DealProgress = ({ deal }) => {
  // determine completed state per step
  const isStepComplete = (key) => {
    switch (key) {
      case "requested":
        return !!deal;
      case "agreed":
        return deal.organizerAccepted && deal.sponsorAccepted;
      case "payment":
        return !!deal.paymentDone;
      case "signed":
        return deal.organizerSigned && deal.sponsorSigned;
      case "closed":
        return deal.status === "closed";
      default:
        return false;
    }
  };

  return (
    <div className="deal-progress-container">
      {steps.map((step, index) => {
        const complete = isStepComplete(step.key);
        const nextComplete = index < steps.length - 1 && isStepComplete(steps[index + 1].key);
        return (
          <React.Fragment key={step.key}>
            <div className={`step ${complete ? "complete" : "pending"}`}>
              <span className="step-label">{step.label}</span>
              <span className="step-circle" />
            </div>
            {index < steps.length - 1 && (
              <div className={`connector ${nextComplete ? "complete" : "pending"}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

export default DealProgress;
