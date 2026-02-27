import React, { useEffect, useRef } from "react";
import { fireConfetti } from "../utils/confetti";

const DealCard = ({ deal, children }) => {
  const prevStatus = useRef(deal.status);

  useEffect(() => {
    if (deal.status === "closed" && prevStatus.current !== "closed") {
      fireConfetti();
    }
    prevStatus.current = deal.status;
  }, [deal.status]);

  return <div className="deal-flow-card">{children}</div>;
};

export default DealCard;
