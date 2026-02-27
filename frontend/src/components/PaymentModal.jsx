import React, { useState } from "react";
import "./PaymentModal.css";

const PaymentModal = ({ amount, currency, onSuccess, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [method, setMethod] = useState("card"); // 'card', 'upi', 'netbanking'
  const [inputAmount, setInputAmount] = useState(amount && Number(amount) > 0 ? String(amount) : "0");
  const [selectedBank, setSelectedBank] = useState("");
  
  React.useEffect(() => {
    if (amount) setInputAmount(String(amount));
  }, [amount]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (loading) return;

    if (Number(inputAmount) <= 0) {
      alert("Please enter a valid payment amount.");
      return;
    }

    setLoading(true);
    
    // Simulate payment processing logic
    setTimeout(() => {
      setLoading(false);
      if (onSuccess) onSuccess({
        amount: Number(inputAmount),
        currency,
        method,
        details: method === 'netbanking' ? { bank: selectedBank } : {}
      });
    }, 2500);
  };

  return (
    <div className="payment-modal-overlay" onClick={onClose}>
      <div className="payment-modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="payment-modal-close" onClick={onClose}>✕</button>
        
        <header className="payment-header">
          <h2>Secure Checkout</h2>
          <div className="amount-display">
            <span className="label">Amount to Pay</span>
            <div className="amount-input-wrapper">
              <span className="currency-symbol">{currency === "INR" ? "₹" : "$"}</span>
              <input 
                type="number" 
                className="payment-amount-input" 
                value={inputAmount} 
                onChange={(e) => setInputAmount(e.target.value)}
                placeholder="0.00"
              />
            </div>
          </div>
        </header>

        <div className="payment-methods-tabs">
          <button 
            className={`method-tab ${method === 'card' ? 'active' : ''}`}
            onClick={() => setMethod('card')}
          >
            <span className="icon">💳</span>
            <span className="text">Card</span>
          </button>
          <button 
            className={`method-tab ${method === 'upi' ? 'active' : ''}`}
            onClick={() => setMethod('upi')}
          >
            <span className="icon">📱</span>
            <span className="text">UPI</span>
          </button>
          <button 
            className={`method-tab ${method === 'netbanking' ? 'active' : ''}`}
            onClick={() => setMethod('netbanking')}
          >
            <span className="icon">🏦</span>
            <span className="text">Banking</span>
          </button>
        </div>

        <form className="payment-form" onSubmit={handleSubmit}>
          {method === "card" && (
            <div className="method-fields animate-fade-in">
              <div className="form-group">
                <label>Cardholder Name</label>
                <input type="text" placeholder="John Doe" required />
              </div>
              <div className="form-group">
                <label>Card Number</label>
                <div className="input-with-icon">
                  <input type="text" placeholder="xxxx xxxx xxxx xxxx" maxLength="19" required />
                  <span className="card-type">VISA</span>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Expiry Date</label>
                  <input type="text" placeholder="MM/YY" maxLength="5" required />
                </div>
                <div className="form-group">
                  <label>CVV</label>
                  <input type="password" placeholder="***" maxLength="3" required />
                </div>
              </div>
            </div>
          )}

          {method === "upi" && (
            <div className="method-fields animate-fade-in">
              <div className="upi-info">
                <div className="qr-placeholder">
                  <div className="qr-icon">📱</div>
                  <p>Scan OR enter UPI ID</p>
                </div>
              </div>
              <div className="form-group">
                <label>UPI ID / VPA</label>
                <div className="upi-input-group">
                  <input type="text" placeholder="username@bank" required />
                  <button type="button" className="verify-btn">Verify</button>
                </div>
                <small className="help-text">Example: 9876543210@paytm</small>
              </div>
            </div>
          )}

          {method === "netbanking" && (
            <div className="method-fields animate-fade-in">
              <div className="form-group">
                <label>Select Your Bank</label>
                <select 
                  className="bank-select" 
                  required 
                  value={selectedBank}
                  onChange={(e) => setSelectedBank(e.target.value)}
                >
                  <option value="">Choose a bank...</option>
                  <option value="sbi">State Bank of India</option>
                  <option value="hdfc">HDFC Bank</option>
                  <option value="icici">ICICI Bank</option>
                  <option value="axis">Axis Bank</option>
                  <option value="kotak">Kotak Mahindra Bank</option>
                </select>
              </div>
              <div className="popular-banks">
                <p>Popular Banks</p>
                <div className="bank-grid">
                  <div 
                    className={`bank-item ${selectedBank === 'sbi' ? 'active' : ''}`}
                    onClick={() => setSelectedBank('sbi')}
                  >
                    SBI
                  </div>
                  <div 
                    className={`bank-item ${selectedBank === 'hdfc' ? 'active' : ''}`}
                    onClick={() => setSelectedBank('hdfc')}
                  >
                    HDFC
                  </div>
                  <div 
                    className={`bank-item ${selectedBank === 'icici' ? 'active' : ''}`}
                    onClick={() => setSelectedBank('icici')}
                  >
                    ICICI
                  </div>
                  <div 
                    className={`bank-item ${selectedBank === 'axis' ? 'active' : ''}`}
                    onClick={() => setSelectedBank('axis')}
                  >
                    AXIS
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="payment-footer">
            <p className="security-note">🔒 Encrypted 256-bit secure payment</p>
            <button type="submit" disabled={loading} className="pay-now-btn">
              {loading ? (
                <div className="loader-container">
                  <span className="spinner"></span>
                  <span>Processing...</span>
                </div>
              ) : (
                `Pay ${currency === "INR" ? "₹" : "$"}${Number(inputAmount).toLocaleString()}`
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PaymentModal;
