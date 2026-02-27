import jsPDF from "jspdf";
import { formatCurrency } from "./formatCurrency";

export function generateInvoicePDF(deal) {
  const doc = new jsPDF();
  const lineHeight = 10;
  let y = 20;

  doc.setFontSize(16);
  doc.text("Invoice", 105, y, { align: "center" });
  y += lineHeight * 2;

  doc.setFontSize(12);
  doc.text(`Deal ID: ${deal.id || "N/A"}`, 20, y);
  y += lineHeight;
  doc.text(`Organizer: ${deal.organizerName || "N/A"}`, 20, y);
  y += lineHeight;
  doc.text(`Sponsor: ${deal.sponsorName || "N/A"}`, 20, y);
  y += lineHeight;
  const amount = deal.paymentAmount != null ? deal.paymentAmount : deal.amount;
  const currency = deal.currency || "";
  doc.text(`Amount: ${amount != null ? formatCurrency(amount, currency) : "N/A"}`, 20, y);
  y += lineHeight;
  const date = deal.date ? new Date(deal.date).toLocaleDateString() : "N/A";
  doc.text(`Date: ${date}`, 20, y);
  y += lineHeight;
  const status = deal.paymentDone ? "Paid" : "Pending";
  doc.text(`Payment status: ${status}`, 20, y);
  y += lineHeight;
  // signatures
  if (deal.organizerSigned) {
    const when = deal.organizerSignedAt
      ? new Date(deal.organizerSignedAt).toLocaleString()
      : "";
    doc.text(`Organizer signed: ${deal.organizerSignature || ""}`, 20, y);
    y += lineHeight;
    if (when) {
      doc.text(`  at ${when}`, 20, y);
      y += lineHeight;
    }
  }
  if (deal.sponsorSigned) {
    const when = deal.sponsorSignedAt
      ? new Date(deal.sponsorSignedAt).toLocaleString()
      : "";
    doc.text(`Sponsor signed: ${deal.sponsorSignature || ""}`, 20, y);
    y += lineHeight;
    if (when) {
      doc.text(`  at ${when}`, 20, y);
      y += lineHeight;
    }
  }

  doc.save(`invoice_${deal.id || "unknown"}.pdf`);
}
