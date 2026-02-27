import React, { useState } from "react";
import "./ReviewModal.css";

const ReviewModal = ({ deal, reviewerRole, targetRole, onSubmit, onClose }) => {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        deal_id: deal.id,
        rating,
        comment,
        reviewer_role: reviewerRole,
        target_role: targetRole,
      });
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="review-modal-overlay" onClick={onClose}>
      <div className="review-modal-content glass-morphism" onClick={(e) => e.stopPropagation()}>
        <button className="review-modal-close" onClick={onClose}>×</button>
        <header className="review-modal-header">
          <h2>Share Your Feedback</h2>
          <p>How was your experience working with <strong>{targetRole === 'sponsor' ? deal.sponsorName : (targetRole === 'organizer' ? deal.organizerName : 'Creator')}</strong>?</p>
        </header>

        <form onSubmit={handleSubmit} className="review-form">
          <div className="rating-selector">
            <label>Rate your experience (1-5)</label>
            <div className="star-rating">
              {[1, 2, 3, 4, 5].map((star) => (
                <span
                  key={star}
                  className={`star ${star <= rating ? "filled" : ""}`}
                  onClick={() => setRating(star)}
                >
                  ★
                </span>
              ))}
            </div>
          </div>

          <div className="comment-box">
            <label>Comments</label>
            <textarea
              placeholder="Tell us more about the collaboration..."
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows="4"
              required
            ></textarea>
          </div>

          <button type="submit" disabled={submitting} className="submit-review-btn">
            {submitting ? "Submitting..." : "Submit Review"}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ReviewModal;
