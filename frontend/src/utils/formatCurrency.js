export const formatCurrency = (amount, currency = "INR") => {
  const numericAmount = Number(amount);
  const safeAmount = Number.isFinite(numericAmount) ? numericAmount : 0;

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
  }).format(safeAmount);
};
