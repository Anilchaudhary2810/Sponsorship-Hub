import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import ChatBox from "../components/ChatBox";
import DashboardStats from "../components/DashboardStats";
import EmptyState from "../components/EmptyState";
import DealCard from "../components/DealCard";
import { formatCurrency } from "../utils/formatCurrency";
import { mapDealData } from "../utils/mapping";
import "./InfluencerDashboard.css";
import {
  fetchCampaigns,
  fetchDeals,
  createDeal,
  acceptDeal,
  signDeal as signDealFn,
  createReview,
  fetchMyReviews,
} from "../services/api";
import AgreementModal from "../components/AgreementModal";
import ReviewModal from "../components/ReviewModal";

const InfluencerDashboard = () => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [deals, setDeals] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeDealChat, setActiveDealChat] = useState(null);
  const [currentUser] = useState(() => JSON.parse(localStorage.getItem("currentUser") || "{}"));
  const [signDeal, setSignDeal] = useState(null);
  const [showAgreementModal, setShowAgreementModal] = useState(false);
  const [reviewDeal, setReviewDeal] = useState(null);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewedDeals, setReviewedDeals] = useState({}); // { dealId: rating }
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const loadData = async () => {
    try {
      const [campResp, dealsResp] = await Promise.all([
        fetchCampaigns(),
        fetchDeals()
      ]);
      setCampaigns(campResp.data);
      const myDeals = dealsResp.data.filter(d => Number(d.influencer_id) === Number(currentUser.id));
      setDeals(myDeals.map(d => mapDealData(d, currentUser)));

      // Load past reviews so stars persist across page refreshes
      try {
        const myReviewsResp = await fetchMyReviews();
        const map = {};
        Object.entries(myReviewsResp.data || {}).forEach(([dealId, rating]) => {
          map[Number(dealId)] = rating;
        });
        setReviewedDeals(prev => ({ ...prev, ...map }));
      } catch {}
    } catch {}
  };

  const refreshDeals = async () => {
    const resp = await fetchDeals();
    const myDeals = resp.data.filter(d => Number(d.influencer_id) === Number(currentUser.id));
    setDeals(myDeals.map(d => mapDealData(d, currentUser)));
  };

  useEffect(() => {
    loadData();

    // Poll for deal updates every 30 s as a lightweight fallback.
    // Real-time updates are handled by the NotificationBell WebSocket (in Navbar).
    const pollInterval = setInterval(() => {
      refreshDeals();
    }, 30000);

    return () => clearInterval(pollInterval);
  }, [currentUser.id]);

  const handleApply = async (campaign) => {
    setIsSubmitting(true);
    try {
      await createDeal({
        influencer_id: currentUser.id,
        sponsor_id: campaign.creator_id,
        campaign_id: campaign.id,
        deal_type: "promotion"
      });
      toast.success("Proposal Sent to Sponsor!");
      refreshDeals();
    } catch {
    } finally { setIsSubmitting(false); }
  };

  const handleDealAction = async (dealId, actionFn, payload) => {
    setIsSubmitting(true);
    try {
      await actionFn(dealId, payload);
      await refreshDeals();
      toast.success("Pipeline Updated");
    } catch {
    } finally { setIsSubmitting(false); }
  };

  const handleStartSigning = (deal) => {
    setSignDeal({ ...deal, content: `CAMPAIGN PARTNERSHIP AGREEMENT\nBetween ${deal.sponsorName} and ${deal.influencer?.full_name || 'Creator'}\nCampaign: ${deal.campaign?.title}\nPayment: ${deal.paymentAmount} ${deal.currency}` });
    setShowAgreementModal(true);
  };

  const handleSignSuccess = (signature) => {
    handleDealAction(signDeal.id, signDealFn, { role: "influencer", signature });
    setShowAgreementModal(false);
  };

  const handleReviewSubmit = async (reviewData) => {
    try {
      await createReview({
        ...reviewData,
        reviewer_id: currentUser.id
      });
      setReviewedDeals(prev => ({ ...prev, [reviewDeal.id]: reviewData.rating }));
      setShowReviewModal(false);
      setReviewDeal(null);
      toast.success("⭐ Review submitted! Thank you.");
      loadData();
    } catch {}
  };

  const stats = [
    { title: "Live Campaigns", value: campaigns.length },
    { title: "Active Deals", value: deals.filter(d => d.status !== 'closed' && d.status !== 'rejected').length },
    { title: "Projected Earnings", value: formatCurrency(deals.filter(d => d.status === 'signed').reduce((s, d) => s + (Number(d.paymentAmount) || 0), 0)) },
  ];

  return (
    <div>
      <Navbar role="influencer" />
      <div className="influencer-container">
        <header className="dashboard-header-horizontal">
          <div className="header-main-info">
            <div className="title-action-row">
              <h1 className="influencer-title">Creator Studio</h1>
              <button className="analytics-nav-btn" onClick={() => navigate('/analytics')}>
                📊 Analytics
              </button>
            </div>
            <p className="subtitle">Collaborate with premium brands and manage your campaigns.</p>
          </div>
        </header>

        <DashboardStats stats={stats} />

        <div className="horizontal-sections-stack">
          {/* Active Deals Section */}
          <section className="dashboard-section-wide">
            <div className="section-header">
              <h2>My Brand Pipeline</h2>
              <span className="badge">{deals.length} Connections</span>
            </div>
            <div className="horizontal-scroll-container">
              <div className="deal-pipeline-grid">
                {deals.filter(d => d.status !== 'rejected').map(deal => (
                  <DealCard key={deal.id} deal={deal}>
                    <div className="deal-card-content-wide">
                      <h4 className="deal-title-mini">{deal.campaign?.title || "Brand Partnership"}</h4>
                      <p className="deal-sponsor-name">
                        Client: 
                        <span
                          className="profile-link"
                          onClick={() => navigate(`/profile/${deal.sponsor_id}`)}
                          title="View Sponsor Profile"
                        >
                          {deal.sponsorName}
                        </span>
                      </p>
                      <div className="status-grid">
                        <span className={`status-pill ${deal.status}`}>{deal.status.replace('_', ' ')}</span>
                        <span className={`status-item ${deal.paymentDone ? 'done' : 'pending'}`}>
                          {deal.paymentDone ? '✅ Paid' : (deal.status === 'payment_pending' ? '⏳ Awaiting' : '⏳ Pending')}
                        </span>
                      </div>
                      <div className="deal-actions-row">
                        {deal.status === 'proposed' && !deal.influencerAccepted && (
                          <>
                            <button className="mini-action-btn primary" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "influencer", accept: true })}>✓ Accept</button>
                            <button className="mini-action-btn reject" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "influencer", accept: false })}>✕ Decline</button>
                          </>
                        )}
                        {deal.paymentDone && !deal.influencerSigned && (
                          <button className="mini-action-btn legal" onClick={() => handleStartSigning(deal)}>📄 Sign</button>
                        )}
                        {deal.influencerSigned && (
                          <button className="mini-action-btn primary-outline" onClick={() => handleStartSigning(deal)}>📄 Agreement</button>
                        )}
                        {deal.status === 'closed' && (
                          reviewedDeals[deal.id] ? (
                            <div className="reviewed-badge">
                              {Array.from({ length: 5 }, (_, i) => (
                                <span key={i} className={i < reviewedDeals[deal.id] ? 'rstar filled' : 'rstar'}>★</span>
                              ))}
                              <span className="reviewed-label">Reviewed</span>
                            </div>
                          ) : (
                            <button
                              className="mini-action-btn review"
                              onClick={() => {
                                setReviewDeal(deal);
                                setShowReviewModal(true);
                              }}
                            >
                              ⭐ Review
                            </button>
                          )
                        )}
                        <button className="mini-action-btn chat" onClick={() => setActiveDealChat(deal)}>💬 Chat</button>
                      </div>
                    </div>
                  </DealCard>
                ))}
                {deals.filter(d => d.status !== 'rejected').length === 0 && <EmptyState title="Pipeline empty" description="Apply to campaigns or wait for brand invites." />}
              </div>
            </div>
          </section>

          {/* Campaign Marketplace */}
          <section className="dashboard-section-wide">
            <div className="section-header marketplace-header-row">
              <div className="section-title-group">
                <div className="title-with-action">
                  <h2>Brand Opportunities</h2>
                  <button 
                    className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
                    onClick={() => setShowFilters(!showFilters)}
                  >
                    🔍 {showFilters ? 'Hide Filters' : 'Search & Filters'}
                  </button>
                </div>
                <p>Explore open campaigns looking for creative talent.</p>
              </div>

              {showFilters && (
                <div className="marketplace-filters-bar glass-morphism animate-in">
                  <input 
                    type="text" 
                    placeholder="Search campaigns, platforms, or niches..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="search-input"
                  />
                </div>
              )}
            </div>
            <div className="campaign-horizontal-grid">
              {campaigns.filter(c => 
                c.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                c.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
                c.platform_required.toLowerCase().includes(searchTerm.toLowerCase())
              ).map(camp => {
                const isApplied = deals.some(d => Number(d.campaign_id) === Number(camp.id));
                return (
                  <div key={camp.id} className="campaign-card-modern">
                    <div className="campaign-badge">{camp.platform_required}</div>
                    <h3 className="campaign-card-title">{camp.title}</h3>
                    <p className="campaign-card-desc">{camp.description}</p>
                    <div className="campaign-meta-info">
                      <div className="meta-item"><span>💰</span> {formatCurrency(camp.budget)}</div>
                      <div className="meta-item"><span>📦</span> {camp.deliverables}</div>
                    </div>
                    <div className="marketplace-actions-row">
                      {isApplied ? (
                        <button className="applied-pill-btn" disabled>Already Applied</button>
                      ) : (
                        <button className="accept-pill-btn" onClick={() => handleApply(camp)} disabled={isSubmitting}>
                          {isSubmitting ? "Processing..." : "Apply Now"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </div>
      {activeDealChat && <ChatBox role="influencer" title={`Chat: ${activeDealChat.sponsorName}`} chatKey={`deal_${activeDealChat.id}`} onClose={() => setActiveDealChat(null)} />}
      {showAgreementModal && <AgreementModal deal={signDeal} role="influencer" onSign={handleSignSuccess} onClose={() => setShowAgreementModal(false)} />}
      {showReviewModal && (
        <ReviewModal 
          deal={reviewDeal} 
          reviewerRole="influencer" 
          targetRole="sponsor" 
          onSubmit={handleReviewSubmit} 
          onClose={() => setShowReviewModal(false)} 
        />
      )}
    </div>
  );
};

export default InfluencerDashboard;
