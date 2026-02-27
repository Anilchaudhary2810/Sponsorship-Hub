import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import ChatBox from "../components/ChatBox";
import DashboardStats from "../components/DashboardStats";
import EmptyState from "../components/EmptyState";
import DealCard from "../components/DealCard";
import PaymentModal from "../components/PaymentModal";
import AgreementModal from "../components/AgreementModal";
import DocumentViewer from "../components/DocumentViewer";
import AnalyticsPanel from "../components/AnalyticsPanel";
import { formatCurrency } from "../utils/formatCurrency";
import { mapEventData, mapDealData } from "../utils/mapping";
import EventDetailModal from "../components/EventDetailModal";
import { INDIAN_STATES } from "../utils/constants";
import "./SponsorDashboard.css";
import {
  acceptDeal,
  fetchEvents,
  fetchDeals,
  markPaymentDone,
  signDeal as signDealFn,
  createDeal,
  createReview,
  fetchMyReviews,
  fetchCampaigns,
  createCampaign,
  getAvailableInfluencers,
} from "../services/api";
import ReviewModal from "../components/ReviewModal";

const SponsorDashboard = () => {
  const navigate = useNavigate();
  const [activePipeline, setActivePipeline] = useState("events"); // 'events' or 'influencers'
  const indianStates = INDIAN_STATES;
  const [selectedState, setSelectedState] = useState("All States");
  
  const [events, setEvents] = useState([]);
  const [deals, setDeals] = useState([]);
  const [influencers, setInfluencers] = useState([]);
  const [myCampaigns, setMyCampaigns] = useState([]);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeDealChat, setActiveDealChat] = useState(null);
  const [hiddenEventIds, setHiddenEventIds] = useState([]);
  const [hiddenInfluencerIds, setHiddenInfluencerIds] = useState([]);
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [itemToReject, setItemToReject] = useState(null);

  const [isCreateCampaignOpen, setIsCreateCampaignOpen] = useState(false);
  const [campaignFormData, setCampaignFormData] = useState({
    title: "", description: "", budget: "", platform_required: "Instagram", deliverables: ""
  });

  const [reviewDeal, setReviewDeal] = useState(null);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewedDeals, setReviewedDeals] = useState({}); // { dealId: rating }
  const [selectedEventDetails, setSelectedEventDetails] = useState(null);
  const [showDocument, setShowDocument] = useState(null); // { type: 'agreement'|'invoice', deal }

  const [currentUser] = useState(() => JSON.parse(localStorage.getItem("currentUser") || "{}"));

  // --- Search & Filter State ---
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("All Categories");
  const [filterCity, setFilterCity] = useState("All Cities");
  const [minBudget, setMinBudget] = useState("");
  const [maxBudget, setMaxBudget] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const loadData = async () => {
    try {
      const [eventsResp, dealsResp, influencersResp, campaignsResp] = await Promise.all([
        fetchEvents(), 
        fetchDeals(),
        getAvailableInfluencers(),
        fetchCampaigns()
      ]);
      
      setEvents(eventsResp.data.map(mapEventData));
      
      const mine = dealsResp.data.filter(d => Number(d.sponsor_id) === Number(currentUser.id));
      setDeals(mine.map(d => mapDealData(d, currentUser)));

      setInfluencers(influencersResp
        .filter(u => !u.full_name?.toLowerCase().includes("test") && !u.email?.toLowerCase().includes("test"))
        .map(u => ({
          id: u.id,
          name: u.full_name,
          niche: u.niche || "General",
          audience: u.audience_size || 0,
          platforms: u.platforms || "Social Media",
          about: u.about || "N/A",
          avatar: u.instagram_handle ? `https://unavatar.io/instagram/${u.instagram_handle}` : null
        })));

      setMyCampaigns(campaignsResp.data.filter(c => Number(c.creator_id) === Number(currentUser.id)));

      // Load past reviews so stars persist across page refreshes
      try {
        const myReviewsResp = await fetchMyReviews();
        // myReviewsResp.data = { "dealId": rating, ... }
        const map = {};
        Object.entries(myReviewsResp.data || {}).forEach(([dealId, rating]) => {
          map[Number(dealId)] = rating;
        });
        setReviewedDeals(prev => ({ ...prev, ...map }));
      } catch {}
    } catch {}
  };

  useEffect(() => {
    // 0. Force sync currentUser from localStorage to catch any post-login/register updates
    const userFromStorage = JSON.parse(localStorage.getItem("currentUser") || "{}");
    
    loadData();

    // Setup real-time notifications
    const token = localStorage.getItem("authToken");
    const userId = userFromStorage.id;
    if (!userId || !token) return;

    const apiBase = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
    const wsHost = apiBase.replace(/^http/, "ws");
    const wsUrl = `${wsHost}/ws/notifications/${userId}?token=${token}`;
    const socket = new WebSocket(wsUrl);
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("Real-time Update:", data);
      
      if (data.type === "MARKETPLACE_REFRESH") {
        loadData(); // Re-fetch all if marketplace changes
      } else if (data.type === "DEAL_UPDATE") {
        refreshDeals();
      }
    };

    socket.onclose = () => console.log("Notification Socket closed");
    socket.onerror = (err) => console.error("Notification Socket error:", err);

    return () => socket.close();
  }, [currentUser.id]);

  const refreshDeals = async () => {
    const resp = await fetchDeals();
    const mine = resp.data.filter(d => Number(d.sponsor_id) === Number(currentUser.id));
    setDeals(mine.map(d => mapDealData(d, currentUser)));
  };

  const handleDealAction = async (dealId, actionFn, payload) => {
    setIsSubmitting(true);
    try {
      if (payload.accept === false) {
        if (!window.confirm("Are you sure you want to reject this deal?")) return;
      }
      await actionFn(dealId, payload);
      await refreshDeals();
      toast.success("Ecosystem Updated");
    } catch {
    } finally { setIsSubmitting(false); }
  };

  const [paymentDeal, setPaymentDeal] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  
  const [signDeal, setSignDeal] = useState(null);
  const [showAgreementModal, setShowAgreementModal] = useState(false);

  const handleStartPayment = (deal) => { 
    // If the deal has no amount yet, try to use the event budget as a suggestion
    let suggestedAmount = Number(deal.paymentAmount);
    if (suggestedAmount === 0) {
      if (deal.event) {
        suggestedAmount = Number(deal.event.raw_budget);
      } else if (deal.campaign) {
        suggestedAmount = Number(deal.campaign.budget);
      }
    }
    
    setPaymentDeal({ ...deal, paymentAmount: suggestedAmount }); 
    setShowPaymentModal(true); 
  };
  const handlePaymentSuccess = async (pay) => {
    await handleDealAction(paymentDeal.id, markPaymentDone, { ...pay, payment_by: "sponsor" });
    setShowPaymentModal(false);
  };

  const handleStartSigning = (deal) => {
    setSignDeal({ ...deal, content: `LEGAL SPONSORSHIP AGREEMENT\nBetween ${deal.organizerName} and ${deal.sponsorName}\nAmount: ${deal.paymentAmount} ${deal.currency}` });
    setShowAgreementModal(true);
  };

  const handleSignSuccess = (signature) => {
    handleDealAction(signDeal.id, signDealFn, { role: "sponsor", signature });
    setShowAgreementModal(false);
  };

  const handleReviewSubmit = async (reviewData) => {
    try {
      await createReview({
        ...reviewData,
        reviewer_id: currentUser.id
      });
      // Mark this deal as reviewed with the given rating
      setReviewedDeals(prev => ({ ...prev, [reviewDeal.id]: reviewData.rating }));
      setShowReviewModal(false);
      setReviewDeal(null);
      toast.success("⭐ Review submitted! Thank you for your feedback.");
      loadData();
    } catch {}
  };

  const [proposeDealEvent, setProposeDealEvent] = useState(null);
  const [showProposeDialog, setShowProposeDialog] = useState(false);

  const confirmProposeDeal = async () => {
    if (!proposeDealEvent) return;
    setIsSubmitting(true);
    try {
      await createDeal({ 
        sponsor_id: currentUser.id, 
        organizer_id: proposeDealEvent.organizer_id, 
        event_id: proposeDealEvent.id,
        deal_type: "sponsorship" // Added required field to fix 422 error
      });
      await refreshDeals();
      toast.success("Partnership Proposal Sent!");
      setShowProposeDialog(false);
    } catch {
    } finally { 
      setIsSubmitting(false);
      setProposeDealEvent(null);
    }
  };

  const handleProposeDeal = (event) => {
    setProposeDealEvent(event);
    setShowProposeDialog(true);
  };

  const handleCreateCampaign = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await createCampaign({ ...campaignFormData, creator_id: currentUser.id });
      toast.success("Brand Campaign Published!");
      setIsCreateCampaignOpen(false);
      setCampaignFormData({ title: "", description: "", budget: "", platform_required: "Instagram", deliverables: "" });
      loadData();
    } catch {
    } finally { setIsSubmitting(false); }
  };

  const [proposeInfluencer, setProposeInfluencer] = useState(null);
  const [showInfluencerDialog, setShowInfluencerDialog] = useState(false);
  const [selectedCampaignId, setSelectedCampaignId] = useState("");

  const confirmInfluencerProposal = async () => {
    if (!selectedCampaignId || !proposeInfluencer) return;
    setIsSubmitting(true);
    try {
      await createDeal({
        sponsor_id: currentUser.id,
        influencer_id: proposeInfluencer.id,
        campaign_id: selectedCampaignId,
        deal_type: "promotion"
      });
      await refreshDeals();
      toast.success("Campaign Proposal Sent!");
      setShowInfluencerDialog(false);
    } catch {
    } finally { setIsSubmitting(false); }
  };

  const filteredEvents = events.filter(e => {
    if (hiddenEventIds.includes(e.id)) return false;
    const matchesState = selectedState === "All States" || e.state === selectedState;
    const matchesSearch = 
      e.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
      e.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.about?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.city?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.state?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = filterCategory === "All Categories" || e.category === filterCategory;
    const matchesCity = filterCity === "All Cities" || e.city === filterCity;
    const matchesBudget = (!minBudget || e.budget >= Number(minBudget)) && (!maxBudget || e.budget <= Number(maxBudget));
    return matchesState && matchesSearch && matchesCategory && matchesCity && matchesBudget;
  });

  const filteredInfluencers = influencers.filter(i => {
    if (hiddenInfluencerIds.includes(i.id)) return false;
    const matchesSearch = i.name.toLowerCase().includes(searchTerm.toLowerCase()) || i.niche.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesNiche = filterCategory === "All Categories" || i.niche === filterCategory;
    const matchesAudience = !minBudget || i.audience >= Number(minBudget);
    return matchesSearch && matchesNiche && matchesAudience;
  });

  const uniqueCategories = ["All Categories", ...new Set(activePipeline === 'events' ? events.map(e => e.category) : influencers.map(i => i.niche))].filter(Boolean);
  const uniqueCities = ["All Cities", ...new Set(events.map(e => e.city))].filter(Boolean);

  const filteredDeals = deals.filter(d => 
    activePipeline === 'events' ? d.deal_type === 'sponsorship' : d.deal_type === 'promotion'
  );

  const stats = [
    { 
      title: activePipeline === 'events' ? "Marketplace Events" : "Creator Selection", 
      value: activePipeline === 'events' ? filteredEvents.length : filteredInfluencers.length 
    },
    { 
      title: "Active Partnerships", 
      value: filteredDeals.filter(d => d.status !== 'closed' && d.status !== 'rejected').length 
    },
    { 
      title: "Category Spend", 
      value: formatCurrency(filteredDeals.filter(d => d.paymentDone).reduce((s, d) => s + (Number(d.paymentAmount) || 0), 0)) 
    }
  ];

  return (
    <div>
      <Navbar role="sponsor" />
      <div className="sponsor-container">
        <header className="dashboard-header-horizontal">
          <div className="header-main-info">
            <div className="title-action-row">
              <h1 className="sponsor-title">Sponsor Command Center</h1>
              <button className="analytics-nav-btn" onClick={() => navigate('/analytics')}>
                📊 Analytics
              </button>
            </div>
            <p className="subtitle">Manage all your partnerships across events and creators.</p>
          </div>
          <div className="pipeline-switcher-container">
            <div className="pipeline-tabs">
              <button className={`pipeline-tab-btn ${activePipeline === 'events' ? 'active' : ''}`} onClick={() => setActivePipeline('events')}>
                🏟️ Event Sponsorships
              </button>
              <button className={`pipeline-tab-btn ${activePipeline === 'influencers' ? 'active' : ''}`} onClick={() => setActivePipeline('influencers')}>
                🤳 Creator Marketing
              </button>
            </div>
          </div>
          <div className="header-actions">
            {activePipeline === 'influencers' && (
              <button className="create-primary-btn" onClick={() => setIsCreateCampaignOpen(true)}>
                📣 New Campaign
              </button>
            )}
            {activePipeline === 'events' && (
              <div className="header-filters">
                <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)} className="horizontal-select">
                  {indianStates.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
            )}
          </div>
        </header>

        {isCreateCampaignOpen && (
          <div className="create-event-overlay-horizontal">
            <div className="create-event-card-horizontal">
              <header className="form-header-compact">
                <h2>Launch New Campaign</h2>
                <button className="close-form-btn" onClick={() => setIsCreateCampaignOpen(false)}>✕</button>
              </header>
              <form className="horizontal-event-form" onSubmit={handleCreateCampaign}>
                <div className="form-grid">
                  <div className="form-group">
                    <label>Campaign Title</label>
                    <input name="title" placeholder="Summer 2024 Launch" required value={campaignFormData.title} onChange={(e) => setCampaignFormData({...campaignFormData, title: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label>Platform</label>
                    <select value={campaignFormData.platform_required} onChange={(e) => setCampaignFormData({...campaignFormData, platform_required: e.target.value})}>
                      <option>Instagram</option>
                      <option>YouTube</option>
                      <option>Twitter</option>
                      <option>TikTok</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Budget (INR)</label>
                    <input type="number" name="budget" placeholder="10000" required value={campaignFormData.budget} onChange={(e) => setCampaignFormData({...campaignFormData, budget: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label>Deliverables</label>
                    <input name="deliverables" placeholder="2 Reels, 1 Story" required value={campaignFormData.deliverables} onChange={(e) => setCampaignFormData({...campaignFormData, deliverables: e.target.value})} />
                  </div>
                  <div className="form-group full-width">
                    <label>Campaign Description</label>
                    <textarea name="description" placeholder="Briefly explain the goal and requirements..." value={campaignFormData.description} onChange={(e) => setCampaignFormData({...campaignFormData, description: e.target.value})} rows="2" />
                  </div>
                </div>
                <div className="form-actions">
                  <button type="submit" className="publish-btn-wide" disabled={isSubmitting}>
                    {isSubmitting ? "Launching..." : "Launch Campaign"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <DashboardStats stats={stats} />

        <div className="horizontal-sections-stack">
          {/* Active Deals Section (Universal) */}
          <section className="dashboard-section-wide">
            <div className="section-header">
              <h2>Active Pipeline</h2>
              <span className="badge">{deals.length} Active Deals</span>
            </div>
            <div className="horizontal-scroll-container">
              <div className="deal-pipeline-grid">
                {deals.filter(d => {
                  if (activePipeline === 'events') return d.deal_type === 'sponsorship';
                  return d.deal_type === 'promotion';
                }).filter(d => d.status !== 'rejected').map(deal => (
                  <DealCard key={deal.id} deal={deal}>
                    <div className="deal-card-content-wide">
                      <h4 className="deal-organizer-name">
                        {deal.deal_type === 'sponsorship' ? (
                          <span
                            className="profile-link"
                            onClick={() => navigate(`/profile/${deal.organizer_id}`)}
                            title="View Profile"
                          >
                            {deal.organizerName}
                          </span>
                        ) : (
                          <span
                            className="profile-link"
                            onClick={() => navigate(`/profile/${deal.influencer_id}`)}
                            title="View Profile"
                          >
                            {deal.influencer?.full_name || 'Creator'}
                          </span>
                        )}
                      </h4>
                      <div className="status-grid">
                        <span className={`status-pill ${deal.status}`}>{deal.status}</span>
                        <span className={`status-item ${deal.paymentDone ? 'done' : 'pending'}`}>
                          {deal.paymentDone ? '✅ Paid' : '⏳ Pending'}
                        </span>
                      </div>
                      <div className="deal-actions-row">
                        {!deal.sponsorAccepted && (
                          <>
                            <button className="mini-action-btn primary" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "sponsor", accept: true })}>Accept</button>
                            <button className="mini-action-btn reject" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "sponsor", accept: false })}>Reject</button>
                          </>
                        )}
                        {deal.status === "payment_pending" && !deal.paymentDone && (
                          <button className="mini-action-btn payment" onClick={() => handleStartPayment(deal)}>Pay</button>
                        )}
                        {deal.paymentDone && !deal.sponsorSigned && <button className="mini-action-btn legal" onClick={() => handleStartSigning(deal)}>Sign</button>}
                        
                        <div className="doc-buttons-group">
                            {deal.sponsorSigned && (
                                <button className="mini-action-btn legal-outline" onClick={() => setShowDocument({ type: 'agreement', deal })}>📄 Agreement</button>
                            )}
                            {deal.paymentDone && (
                                <button className="mini-action-btn primary-outline" onClick={() => setShowDocument({ type: 'invoice', deal })}>🧾 Invoice</button>
                            )}
                        </div>

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
                        <button className="mini-action-btn chat" onClick={() => setActiveDealChat(deal)}>Chat</button>
                      </div>
                    </div>
                  </DealCard>
                ))}
                {deals.filter(d => {
                  if (activePipeline === 'events') return d.deal_type === 'sponsorship';
                  return d.deal_type === 'promotion';
                }).length === 0 && <EmptyState title="No active deals here" description="Explore the marketplace to find new partners." />}
              </div>
            </div>
          </section>

          <section className="dashboard-section-wide">
            <div className="section-header marketplace-header-row">
              <div className="section-title-group">
                <div className="title-with-action">
                  <h2>{activePipeline === 'events' ? 'Event Marketplace' : 'Creator Discovery'}</h2>
                  <button 
                    className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
                    onClick={() => setShowFilters(!showFilters)}
                  >
                    🔍 {showFilters ? 'Hide Filters' : 'Search & Filters'}
                  </button>
                </div>
                <p>{activePipeline === 'events' ? 'Discover premium events looking for sponsors.' : 'Find high-impact creators to boost your brand.'}</p>
              </div>

              {showFilters && (
                <div className="marketplace-filters-bar glass-morphism animate-in">
                <input 
                  type="text" 
                  placeholder={`Search ${activePipeline}...`} 
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="search-input"
                />
                
                <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)} className="filter-select">
                  {uniqueCategories.map(c => <option key={c} value={c}>{c}</option>)}
                </select>

                {activePipeline === 'events' && (
                  <select value={filterCity} onChange={(e) => setFilterCity(e.target.value)} className="filter-select">
                    {uniqueCities.map(city => <option key={city} value={city}>{city}</option>)}
                  </select>
                )}

                <div className="budget-range-group">
                  <input 
                    type="number" 
                    placeholder="Min" 
                    value={minBudget} 
                    onChange={(e) => setMinBudget(e.target.value)}
                    className="budget-input"
                  />
                  <span>-</span>
                  <input 
                    type="number" 
                    placeholder="Max" 
                    value={maxBudget} 
                    onChange={(e) => setMaxBudget(e.target.value)}
                    className="budget-input"
                  />
                </div>
                </div>
              )}
            </div>
            
            {activePipeline === 'events' ? (
              <div className="event-horizontal-grid">
                {filteredEvents.map(event => {
                  const deal = deals.find(d => Number(d.event_id) === Number(event.id));
                  return (
                    <div key={event.id} className="event-card-modern" onClick={() => setSelectedEventDetails(event)} style={{ cursor: "pointer" }}>
                      <div className="event-badge">{event.category || 'Global Event'}</div>
                      <h3 className="event-card-title">{event.title}</h3>
                      <div className="event-meta-info">
                        <p className="meta-item">📍 {event.city}</p>
                        <p className="meta-item price-tag">💰 {formatCurrency(event.budget)}</p>
                      </div>
                      <div className="marketplace-actions-row">
                        {deal ? (
                          <button className="chat-secondary-btn" onClick={(e) => { e.stopPropagation(); setActiveDealChat(deal); }}>💬 Chat</button>
                        ) : (
                          <button className="accept-pill-btn" onClick={(e) => { e.stopPropagation(); handleProposeDeal(event); }}>Propose Deal</button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="creator-horizontal-grid">
                {filteredInfluencers.map(inf => {
                  const deal = deals.find(d => Number(d.influencer_id) === Number(inf.id));
                  return (
                    <div key={inf.id} className="creator-card-modern">
                      <div className="creator-avatar-ring">
                        {inf.avatar ? <img src={inf.avatar} alt={inf.name} className="creator-avatar" /> : <div className="avatar-placeholder">{inf.name[0]}</div>}
                      </div>
                      <h3 className="creator-name">{inf.name}</h3>
                      <p className="creator-niche">{inf.niche}</p>
                      <div className="creator-stats-mini">
                        <span>👥 {inf.audience.toLocaleString()}</span>
                        <span>📱 {inf.platforms}</span>
                      </div>
                      <div className="marketplace-actions-row">
                        {deal ? (
                          <button className="chat-secondary-btn" onClick={() => setActiveDealChat(deal)}>💬 Chat</button>
                        ) : (
                          <button className="accept-pill-btn" onClick={() => { setProposeInfluencer(inf); setShowInfluencerDialog(true); }}>Work Together</button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>


      {showPaymentModal && <PaymentModal amount={paymentDeal.paymentAmount} currency={paymentDeal.currency} onSuccess={handlePaymentSuccess} onClose={() => setShowPaymentModal(false)} />}
      {showAgreementModal && <AgreementModal deal={signDeal} role="sponsor" onSign={handleSignSuccess} onClose={() => setShowAgreementModal(false)} />}
      {activeDealChat && <ChatBox role="sponsor" title={`Chat: ${activeDealChat.organizerName}`} chatKey={`deal_${activeDealChat.id}`} onClose={() => setActiveDealChat(null)} />}
      {isRejectDialogOpen && (
        <div className="delete-dialog-overlay">
          <div className="delete-dialog">
            <h3 className="dialog-title">Ignore Event?</h3>
            <p className="dialog-desc">This event will be hidden from your marketplace view. You can see it again in your next session.</p>
            <div className="delete-dialog-actions">
              <button className="delete-cancel-btn" onClick={() => setIsRejectDialogOpen(false)}>Cancel</button>
              <button className="delete-confirm-btn" onClick={() => { setHiddenEventIds([...hiddenEventIds, eventToReject]); setIsRejectDialogOpen(false); }}>Yes, Ignore</button>
            </div>
          </div>
        </div>
      )}
      {showInfluencerDialog && (
        <div className="delete-dialog-overlay">
          <div className="delete-dialog glass-morphism">
            <div className="dialog-icon">🤳</div>
            <h3 className="dialog-title">Partner with {proposeInfluencer?.name}</h3>
            <p className="dialog-desc">Select one of your pulse-active campaigns to propose to this creator.</p>
            <div className="campaign-selector-list">
              {myCampaigns.map(c => (
                <div 
                  key={c.id} 
                  className={`campaign-item ${selectedCampaignId === c.id ? 'active' : ''}`}
                  onClick={() => setSelectedCampaignId(c.id)}
                >
                  <p className="campaign-name">{c.title}</p>
                  <p className="campaign-meta">{c.deliverables} • {formatCurrency(c.budget)}</p>
                </div>
              ))}
              {myCampaigns.length === 0 && (
                <p className="error-text">You need to launch a campaign first!</p>
              )}
            </div>
            <div className="delete-dialog-actions">
              <button className="delete-cancel-btn" onClick={() => setShowInfluencerDialog(false)}>Cancel</button>
              <button 
                className="delete-confirm-btn proposal-btn" 
                onClick={confirmInfluencerProposal} 
                disabled={!selectedCampaignId || isSubmitting}
              >
                {isSubmitting ? "Sending..." : "Send Proposal"}
              </button>
            </div>
          </div>
        </div>
      )}
      {showProposeDialog && (
        <div className="delete-dialog-overlay">
          <div className="delete-dialog glass-morphism">
            <div className="dialog-icon">🤝</div>
            <h3 className="dialog-title">Secure Partnership?</h3>
            <p className="dialog-desc">
              You are proposing a brand partnership for <strong>{proposeDealEvent?.title}</strong>. 
              The organizer will be notified immediately to review your interest.
            </p>
            <div className="delete-dialog-actions">
              <button className="delete-cancel-btn" onClick={() => setShowProposeDialog(false)}>Cancel</button>
              <button className="delete-confirm-btn proposal-btn" onClick={confirmProposeDeal} disabled={isSubmitting}>
                {isSubmitting ? "Sending..." : "Send Proposal"}
              </button>
            </div>
          </div>
        </div>
      )}
      {showReviewModal && (
        <ReviewModal 
          deal={reviewDeal} 
          reviewerRole="sponsor" 
          targetRole={reviewDeal.deal_type === 'sponsorship' ? 'organizer' : 'influencer'} 
          onSubmit={handleReviewSubmit} 
          onClose={() => setShowReviewModal(false)} 
        />
      )}

      {selectedEventDetails && (
        <EventDetailModal
          event={selectedEventDetails}
          deal={deals.find(d => Number(d.event_id) === Number(selectedEventDetails.id))}
          onClose={() => setSelectedEventDetails(null)}
          onProposeDeal={handleProposeDeal}
          onChat={setActiveDealChat}
          formatCurrency={formatCurrency}
        />
      )}
      {showDocument && (
        <DocumentViewer 
            type={showDocument.type} 
            deal={showDocument.deal} 
            onClose={() => setShowDocument(null)} 
        />
      )}
    </div>
  );
};

export default SponsorDashboard;
