import React from "react";
import { generateInvoicePDF } from "../utils/generateInvoicePDF";
import "./InvoiceButton.css";

const InvoiceButton = ({ deal }) => {
  const handleClick = () => {
    generateInvoicePDF(deal);
  };

  return (
    <button onClick={handleClick} className="invoice-button">
      Download Invoice
    </button>
  );
};

export default InvoiceButton;
