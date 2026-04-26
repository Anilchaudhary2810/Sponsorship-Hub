import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
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
import QuickActionsBar from "../components/QuickActionsBar";
import "./SponsorDashboard.css";
import ActivityProgressModal from "../components/ActivityProgressModal";
import {
  acceptDeal,
  fetchEvents,
  fetchDeals,
  fetchDeal,
  createPaymentOrder,
  fetchPaymentCheckoutConfig,
  signDeal as signDealFn,
  createDeal,
  createReview,
  fetchMyReviews,
  fetchCampaigns,
  createCampaign,
  getAvailableInfluencers,
} from "../services/api";
import ReviewModal from "../components/ReviewModal";

const loadRazorpaySdk = () =>
  new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      reject(new Error("Window not available"));
      return;
    }
    if (window.Razorpay) {
      resolve(window.Razorpay);
      return;
    }

    const existing = document.getElementById("razorpay-checkout-sdk");
    if (existing) {
      existing.addEventListener("load", () => resolve(window.Razorpay));
      existing.addEventListener("error", () => reject(new Error("Failed to load Razorpay SDK")));
      return;
    }

    const script = document.createElement("script");
    script.id = "razorpay-checkout-sdk";
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.async = true;
    script.onload = () => resolve(window.Razorpay);
    script.onerror = () => reject(new Error("Failed to load Razorpay SDK"));
    document.body.appendChild(script);
  });

const logSponsorError = (scope, err) => {
  console.error(`[SponsorDashboard] ${scope}`, err);
};

const SponsorDashboard = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const dealIdFromQuery = Number(searchParams.get("dealId") || 0);
  const [activePipeline, setActivePipeline] = useState("events"); // 'events' or 'influencers'
  
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
  const [selectedEventDeal, setSelectedEventDeal] = useState(null);
  const [selectedPipelineDeal, setSelectedPipelineDeal] = useState(null);
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
        fetchCampaigns(),
      ]);
      
      setEvents(eventsResp.data.map(mapEventData));
      
      const mine = dealsResp.data.filter(d => Number(d.sponsor_id) === Number(currentUser.id));
      setDeals(mine.map((d) => mapDealData(d, currentUser)));

      setInfluencers(influencersResp
        .map(u => ({
          id: u.id,
          name: u.full_name,
          niche: u.niche || "General",
          audience: u.audience_size || 0,
          platforms: u.platforms || "Social Media",
          about: u.about || "N/A",
          avatar: u.instagram_handle ? `https://unavatar.io/instagram/${u.instagram_handle}` : null
        })));

      setMyCampaigns(campaignsResp.data.filter((c) => Number(c.creator_id) === Number(currentUser.id)));

      // Load past reviews so stars persist across page refreshes
      try {
        const myReviewsResp = await fetchMyReviews();
        // myReviewsResp.data = { "dealId": rating, ... }
        const map = {};
        Object.entries(myReviewsResp.data || {}).forEach(([dealId, rating]) => {
          map[Number(dealId)] = rating;
        });
        setReviewedDeals(prev => ({ ...prev, ...map }));
      } catch (err) {
        logSponsorError("failed to load review history", err);
      }

    } catch (err) {
      logSponsorError("failed to load dashboard data", err);
    }
  };

  useEffect(() => {
    // Load dashboard data with a small delay to ensure auth state is stable
    const timer = setTimeout(() => {
      loadData();
    }, 300);

    // Global listener for real-time refreshes (triggered by WebSockets)
    const handleGlobalRefresh = () => {
      console.log("Real-time refresh triggered");
      loadData();
    };
    window.addEventListener('dashboard-refresh', handleGlobalRefresh);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('dashboard-refresh', handleGlobalRefresh);
    };
  }, [currentUser.id]);

  const refreshDeals = async () => {
    const resp = await fetchDeals();
    const mine = resp.data.filter(d => Number(d.sponsor_id) === Number(currentUser.id));
    setDeals(mine.map((d) => mapDealData(d, currentUser)));
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
    } catch (err) {
      logSponsorError("failed to update deal action", err);
      toast.error("Unable to update deal right now.");
    } finally { setIsSubmitting(false); }
  };

  const [paymentDeal, setPaymentDeal] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  
  const [signDeal, setSignDeal] = useState(null);
  const [showAgreementModal, setShowAgreementModal] = useState(false);

  const handleStartPayment = (deal) => { 
    // Always trust server-provided deal amount only.
    const serverAmount = Number(deal.paymentAmount);
    if (!Number.isFinite(serverAmount) || serverAmount <= 0) {
      toast.error("Deal amount is not configured yet. Please refresh or contact support.");
      return;
    }

    setPaymentDeal({ ...deal, paymentAmount: serverAmount }); 
    setShowPaymentModal(true); 
  };
  const handlePaymentSuccess = async (_pay) => {
    if (!paymentDeal?.id) return;
    setIsSubmitting(true);
    try {
      const [orderResp, configResp] = await Promise.all([
        createPaymentOrder(paymentDeal.id),
        fetchPaymentCheckoutConfig(),
      ]);

      const orderData = orderResp?.data || {};
      const orderId = orderData.razorpay_payment_id;
      const keyId = configResp?.data?.key_id;
      const amountPaise = Math.round(Number(orderData.payment_amount || paymentDeal.paymentAmount || 0) * 100);
      const currency = orderData.currency || paymentDeal.currency || "INR";

      if (!orderId || !keyId || amountPaise <= 0) {
        toast.error("Unable to start gateway checkout. Please verify payment configuration.");
        return;
      }

      await loadRazorpaySdk();
      if (!window.Razorpay) {
        toast.error("Payment SDK unavailable. Please try again.");
        return;
      }

      setShowPaymentModal(false);

      const rzp = new window.Razorpay({
        key: keyId,
        amount: amountPaise,
        currency,
        order_id: orderId,
        name: "Sponsorship Hub",
        description: `Deal #${orderData.id || paymentDeal.id} checkout`,
        handler: async () => {
          toast.success("Payment authorized. Waiting for secure webhook confirmation.");
          await refreshDeals();
        },
        modal: {
          ondismiss: () => {
            toast("Checkout closed. You can retry payment anytime.");
          },
        },
        prefill: {
          name: currentUser.full_name || "",
          email: currentUser.email || "",
        },
        theme: { color: "#5b4bff" },
      });

      rzp.on("payment.failed", () => {
        toast.error("Payment failed. Please try again.");
      });
      rzp.open();

      toast.success("Order created. Complete payment in the gateway popup.");
    } catch (err) {
      logSponsorError("failed to start payment checkout", err);
      toast.error("Unable to start payment checkout");
    } finally {
      setIsSubmitting(false);
    }
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
      toast.success("Review submitted! Thank you for your feedback.");
      loadData();
    } catch (err) {
      logSponsorError("failed to submit review", err);
      toast.error("Unable to submit review.");
    }
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
    } catch (err) {
      logSponsorError("failed to send event proposal", err);
      toast.error("Unable to send proposal.");
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
    } catch (err) {
      logSponsorError("failed to create campaign", err);
      toast.error("Unable to publish campaign.");
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
    } catch (err) {
      logSponsorError("failed to send influencer proposal", err);
      toast.error("Unable to send campaign proposal.");
    } finally { setIsSubmitting(false); }
  };

  const filteredEvents = events.filter(e => {
    if (hiddenEventIds.includes(e.id)) return false;
    const matchesSearch = 
      e.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
      e.description.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.about?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.city?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      e.state?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = filterCategory === "All Categories" || e.category === filterCategory;
    const matchesCity = filterCity === "All Cities" || e.city === filterCity;
    const matchesBudget = (!minBudget || e.budget >= Number(minBudget)) && (!maxBudget || e.budget <= Number(maxBudget));
    return matchesSearch && matchesCategory && matchesCity && matchesBudget;
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

  const getLatestItems = (items, count = 4) =>
    [...items]
      .sort((a, b) => Number(b?.id || 0) - Number(a?.id || 0))
      .slice(0, count);

  const visiblePipelineDeals = filteredDeals.filter((deal) => deal.status !== "rejected");
  const latestPipelineDeals = getLatestItems(visiblePipelineDeals);
  const latestEventMarketplace = getLatestItems(filteredEvents);
  const latestCreatorDiscovery = getLatestItems(filteredInfluencers);

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

  const getDealPartnerName = (deal) => {
    if (deal.deal_type === "sponsorship") return deal.organizerName || "Organizer";
    return deal.influencer?.full_name || deal.influencerName || "Creator";
  };

  const getDealSubject = (deal) => {
    if (deal.deal_type === "sponsorship") return deal.event?.title || "Event partnership";
    return deal.campaign?.title || "Creator campaign";
  };

  const getDealSubline = (deal) => {
    if (deal.deal_type === "sponsorship") {
      const city = deal.event?.city || deal.event?.location || "Location TBD";
      return `${city} - Event Sponsorship`;
    }
    const platform = deal.campaign?.platform_required || "Multi-platform";
    return `${platform} - Creator Promotion`;
  };

  const normalizeEventForModal = (eventLike, fallbackOrganizerId) => {
    if (!eventLike) return null;
    const hasMappedShape = Object.prototype.hasOwnProperty.call(eventLike, "budget");
    if (hasMappedShape) {
      return {
        ...eventLike,
        budget: Number(eventLike.budget ?? eventLike.raw_budget ?? 0),
        organizer_id: Number(eventLike.organizer_id ?? fallbackOrganizerId ?? 0),
        media_items: Array.isArray(eventLike.media_items) ? eventLike.media_items : [],
      };
    }
    const mapped = mapEventData(eventLike);
    return {
      ...mapped,
      organizer_id: Number(mapped.organizer_id || fallbackOrganizerId || 0),
    };
  };

  const openDealEventDetails = (deal) => {
    const fromDealPayload = normalizeEventForModal(deal?.event, deal?.organizer_id);
    const fromMarketplaceList = events.find((evt) => Number(evt.id) === Number(deal?.event_id));
    const eventForModal = fromDealPayload || fromMarketplaceList || null;
    if (!eventForModal) {
      toast.error("Event details are unavailable for this deal.");
      return;
    }
    setSelectedEventDetails(eventForModal);
    setSelectedEventDeal(deal);
  };

  const openDealProgress = (deal) => {
    const dealId = Number(deal?.id || 0);
    if (!dealId) return;

    fetchDeal(dealId)
      .then((resp) => {
        const fresh = mapDealData(resp.data, currentUser);
        setSelectedPipelineDeal(fresh);
      })
      .catch((err) => {
        logSponsorError(`failed to refresh deal #${dealId} details`, err);
        setSelectedPipelineDeal(deal);
      });
  };

  useEffect(() => {
    if (!dealIdFromQuery || !deals.length || selectedPipelineDeal) return;
    const matched = deals.find((deal) => Number(deal.id) === dealIdFromQuery);
    if (matched) {
      openDealProgress(matched);
    }
  }, [dealIdFromQuery, deals, selectedPipelineDeal]);

  const closePipelineDealModal = () => {
    setSelectedPipelineDeal(null);
    if (searchParams.has("dealId")) {
      const next = new URLSearchParams(searchParams);
      next.delete("dealId");
      next.delete("focus");
      setSearchParams(next, { replace: true });
    }
  };

  const goToActivityCenter = (section) => {
    navigate(`/activity-center?section=${section}&pipeline=${activePipeline}`);
  };

  const quickActions = [
    {
      key: "new",
      label: activePipeline === "influencers" ? "New Campaign" : "Filters",
      tone: "primary",
      onClick: () => {
        if (activePipeline === "influencers") setIsCreateCampaignOpen(true);
        else setShowFilters((prev) => !prev);
      },
    },
    { key: "ops", label: "Scale Ops", tone: "emphasis", onClick: () => navigate("/scale-ops") },
    { key: "analytics", label: "Analytics", onClick: () => navigate("/analytics") },
    { key: "profile", label: "Profile", onClick: () => navigate("/my-profile") },
  ];

  return (
    <div>
      <Navbar role="sponsor" />
      <div className="sponsor-container">
        <header className="dashboard-header-horizontal">
          <div className="header-main-info">
            <div className="title-action-row">
              <h1 className="sponsor-title">Sponsor Dashboard</h1>
              <button className="analytics-nav-btn" onClick={() => navigate('/analytics')}>
                Analytics
              </button>
            </div>
            <p className="subtitle">Manage event sponsorships and creator campaigns from one place.</p>
          </div>
          <div className="pipeline-switcher-container">
            <div className="pipeline-tabs">
              <button className={`pipeline-tab-btn ${activePipeline === 'events' ? 'active' : ''}`} onClick={() => setActivePipeline('events')}>
                Event Sponsorships
              </button>
              <button className={`pipeline-tab-btn ${activePipeline === 'influencers' ? 'active' : ''}`} onClick={() => setActivePipeline('influencers')}>
                Creator Marketing
              </button>
            </div>
          </div>
          <div className="header-actions">
            {activePipeline === 'influencers' && (
              <button className="create-primary-btn" onClick={() => setIsCreateCampaignOpen(true)}>
                New Campaign
              </button>
            )}
          </div>
        </header>

        {isCreateCampaignOpen && (
          <div className="create-event-overlay-horizontal">
            <div className="create-event-card-horizontal">
              <header className="form-header-compact">
                <h2>Launch New Campaign</h2>
                <button className="close-form-btn" onClick={() => setIsCreateCampaignOpen(false)}>X</button>
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
        <QuickActionsBar actions={quickActions} />

        <div className="horizontal-sections-stack">
          {/* Active Deals Section (Universal) */}
          <section className="dashboard-section-wide">
            <div className="section-header">
              <h2>
                <button type="button" className="section-nav-link" onClick={() => goToActivityCenter("pipeline")}>
                  Active Pipeline
                </button>
              </h2>
              <span className="badge">{visiblePipelineDeals.length} Active Deals</span>
            </div>
            <div className="horizontal-scroll-container">
              <div className="deal-pipeline-grid h-scroll-grid">
                {latestPipelineDeals.map(deal => (
                  <DealCard key={deal.id} deal={deal}>
                    <div className="deal-card-content-wide">
                      <div className="pipeline-card-head">
                        <div className="deal-type-chip">
                          {deal.deal_type === "sponsorship" ? "Event Deal" : "Creator Deal"}
                        </div>
                        <h4 className="deal-organizer-name">
                          {deal.deal_type === 'sponsorship' ? (
                            <span
                              className="profile-link"
                              onClick={() => navigate(`/profile/${deal.organizer_id}`)}
                              title="View Profile"
                            >
                              {getDealPartnerName(deal)}
                            </span>
                          ) : (
                            <span
                              className="profile-link"
                              onClick={() => navigate(`/profile/${deal.influencer_id}`)}
                              title="View Profile"
                            >
                              {getDealPartnerName(deal)}
                            </span>
                          )}
                        </h4>
                        <button
                          type="button"
                          className="pipeline-activity-link"
                          onClick={() => openDealProgress(deal)}
                          title="Open activity progress"
                        >
                          {getDealSubject(deal)}
                        </button>
                        <p className="deal-context-line">{getDealSubline(deal)}</p>
                      </div>
                      <div className="deal-meta-row">
                        <span className="deal-meta-item">
                          Value: {formatCurrency(Number(deal.paymentAmount) || Number(deal.event?.raw_budget) || Number(deal.campaign?.budget) || 0)}
                        </span>
                        <span className="deal-meta-item">ID: #{deal.id}</span>
                      </div>
                      <div className="status-grid">
                        <span className={`status-pill ${deal.status}`}>{deal.status}</span>
                        <span className={`status-item ${deal.paymentDone ? 'done' : 'pending'}`}>
                          {deal.paymentDone ? "Paid" : "Payment Pending"}
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
                        {deal.status === "closed" ? (
                          reviewedDeals[deal.id] ? (
                            <div className="reviewed-badge">
                              {Array.from({ length: 5 }, (_, i) => (
                                <span key={i} className={i < reviewedDeals[deal.id] ? 'rstar filled' : 'rstar'}>*</span>
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
                              Review
                            </button>
                          )
                        ) : (
                          <button
                            className="mini-action-btn legal"
                            disabled={!deal.paymentDone || deal.sponsorSigned}
                            onClick={() => deal.paymentDone && !deal.sponsorSigned && handleStartSigning(deal)}
                          >
                            Sign
                          </button>
                        )}
                      </div>
                      <div className="pipeline-main-actions">
                        {deal.sponsorSigned && (
                          <button className="mini-action-btn legal-outline" onClick={() => setShowDocument({ type: "agreement", deal })}>Agreement</button>
                        )}
                        {deal.paymentDone && (
                          <button className="mini-action-btn primary-outline invoice-btn" onClick={() => setShowDocument({ type: "invoice", deal })}>Invoice</button>
                        )}
                        <button className="mini-action-btn chat" onClick={() => setActiveDealChat(deal)}>
                          Chat with {deal.deal_type === "sponsorship" ? "Organizer" : "Creator"}
                        </button>
                      </div>
                    </div>
                  </DealCard>
                ))}
                {visiblePipelineDeals.length === 0 && (
                  <EmptyState
                    title="No active deals yet"
                    description="Create a proposal to start your pipeline."
                    actionLabel="Open Marketplace"
                    onAction={() => setShowFilters(true)}
                  />
                )}
              </div>
            </div>
          </section>

          <section className="dashboard-section-wide">
            <div className="section-header marketplace-header-row">
              <div className="section-title-group">
                <div className="title-with-action">
                  <h2>
                    <button
                      type="button"
                      className="section-nav-link"
                      onClick={() => goToActivityCenter(activePipeline === "events" ? "events" : "discovery")}
                    >
                      {activePipeline === "events" ? "Event Marketplace" : "Creator Discovery"}
                    </button>
                  </h2>
                  <button 
                    className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
                    onClick={() => setShowFilters(!showFilters)}
                  >
                    {showFilters ? "Hide Advanced" : "Advanced Filters"}
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
              <div className="event-horizontal-grid h-scroll-grid">
                {latestEventMarketplace.map(event => {
                  const deal = deals.find(d => Number(d.event_id) === Number(event.id));
                  return (
                    <div key={event.id} className="event-card-modern" onClick={() => setSelectedEventDetails(event)} style={{ cursor: "pointer" }}>
                      <div className="event-badge">{event.category || 'Global Event'}</div>
                      <h3 className="event-card-title">{event.title}</h3>
                      <div className="event-meta-info">
                        <p className="meta-item">Location: {event.city}</p>
                        <p className="meta-item price-tag">Budget: {formatCurrency(event.budget)}</p>
                      </div>
                      <div className="marketplace-actions-row">
                        {deal ? (
                          <button className="chat-secondary-btn" onClick={(e) => { e.stopPropagation(); setActiveDealChat(deal); }}>Chat</button>
                        ) : (
                          <button className="accept-pill-btn" onClick={(e) => { e.stopPropagation(); handleProposeDeal(event); }}>Propose Deal</button>
                        )}
                      </div>
                    </div>
                  );
                })}
                {filteredEvents.length === 0 && (
                  <EmptyState
                    title="No events found"
                    description="Adjust search or filters to discover more events."
                    actionLabel="Clear Filters"
                    onAction={() => {
                      setSearchTerm("");
                      setFilterCategory("All Categories");
                      setFilterCity("All Cities");
                      setMinBudget("");
                      setMaxBudget("");
                    }}
                  />
                )}
              </div>
            ) : (
              <div className="creator-horizontal-grid h-scroll-grid">
                {latestCreatorDiscovery.map(inf => {
                  const deal = deals.find(d => Number(d.influencer_id) === Number(inf.id));
                  return (
                    <div key={inf.id} className="creator-card-modern">
                      <div className="creator-avatar-ring">
                        {inf.avatar ? <img src={inf.avatar} alt={inf.name} className="creator-avatar" /> : <div className="avatar-placeholder">{inf.name[0]}</div>}
                      </div>
                      <h3 className="creator-name">{inf.name}</h3>
                      <p className="creator-niche">{inf.niche}</p>
                      <div className="creator-stats-mini">
                        <span>Audience: {inf.audience.toLocaleString()}</span>
                        <span>Platform: {inf.platforms}</span>
                      </div>
                      <div className="marketplace-actions-row">
                        {deal ? (
                          <button className="chat-secondary-btn" onClick={() => setActiveDealChat(deal)}>Chat</button>
                        ) : (
                          <button
                            className="accept-pill-btn"
                            onClick={() => {
                              setSelectedCampaignId("");
                              setProposeInfluencer(inf);
                              setShowInfluencerDialog(true);
                            }}
                          >
                            Work Together
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
                {filteredInfluencers.length === 0 && (
                  <EmptyState
                    title="No creators found"
                    description="Clear filters to view a broader creator set."
                    actionLabel="Clear Filters"
                    onAction={() => {
                      setSearchTerm("");
                      setFilterCategory("All Categories");
                      setMinBudget("");
                    }}
                  />
                )}
              </div>
            )}
          </section>
        </div>
      </div>


      {showPaymentModal && <PaymentModal amount={paymentDeal.paymentAmount} currency={paymentDeal.currency} onSuccess={handlePaymentSuccess} onClose={() => setShowPaymentModal(false)} />}
      {showAgreementModal && <AgreementModal deal={signDeal} role="sponsor" onSign={handleSignSuccess} onClose={() => setShowAgreementModal(false)} />}
      {activeDealChat && (
        <ChatBox
          role="sponsor"
          title={`Chat: ${getDealPartnerName(activeDealChat)} - ${getDealSubject(activeDealChat)}`}
          chatKey={`deal_${activeDealChat.id}`}
          onClose={() => setActiveDealChat(null)}
        />
      )}
      {isRejectDialogOpen && (
        <div className="delete-dialog-overlay">
          <div className="delete-dialog">
            <h3 className="dialog-title">Ignore Event?</h3>
            <p className="dialog-desc">This event will be hidden from your marketplace view. You can see it again in your next session.</p>
            <div className="delete-dialog-actions">
              <button className="delete-cancel-btn" onClick={() => setIsRejectDialogOpen(false)}>Cancel</button>
              <button
                className="delete-confirm-btn"
                onClick={() => {
                  if (itemToReject !== null) {
                    setHiddenEventIds([...hiddenEventIds, itemToReject]);
                  }
                  setItemToReject(null);
                  setIsRejectDialogOpen(false);
                }}
              >
                Yes, Ignore
              </button>
            </div>
          </div>
        </div>
      )}
      {showInfluencerDialog && (
        <div className="proposal-modal-overlay" onClick={() => setShowInfluencerDialog(false)}>
          <div className="proposal-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="proposal-modal-icon">{"\uD83E\uDD33"}</div>
            <h3 className="proposal-modal-title">Partner with {proposeInfluencer?.name}</h3>
            <p className="proposal-modal-desc">Select one of your active campaigns to propose to this creator.</p>
            <div className="campaign-selector-list">
              {myCampaigns.map(c => (
                <div 
                  key={c.id} 
                  className={`campaign-item ${selectedCampaignId === String(c.id) ? 'active' : ''}`}
                  onClick={() => setSelectedCampaignId(String(c.id))}
                >
                  <p className="campaign-name">{c.title}</p>
                  <p className="campaign-meta">{c.deliverables} | {formatCurrency(c.budget)}</p>
                </div>
              ))}
              {myCampaigns.length === 0 && (
                <p className="error-text">You need to launch a campaign first!</p>
              )}
            </div>
            <div className="proposal-modal-actions">
              <button className="proposal-cancel-btn" onClick={() => setShowInfluencerDialog(false)}>Cancel</button>
              <button 
                className="proposal-confirm-btn" 
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
        <div className="proposal-modal-overlay" onClick={() => setShowProposeDialog(false)}>
          <div className="proposal-modal-card compact" onClick={(e) => e.stopPropagation()}>
            <div className="proposal-modal-icon">{"\uD83E\uDD1D"}</div>
            <h3 className="proposal-modal-title">Secure Partnership?</h3>
            <p className="proposal-modal-desc">
              You are proposing a brand partnership for <strong>{proposeDealEvent?.title}</strong>. 
              The organizer will be notified immediately to review your interest.
            </p>
            <div className="proposal-modal-actions">
              <button className="proposal-cancel-btn" onClick={() => setShowProposeDialog(false)}>Cancel</button>
              <button className="proposal-confirm-btn" onClick={confirmProposeDeal} disabled={isSubmitting}>
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

      {selectedPipelineDeal && (
        <ActivityProgressModal
          deal={selectedPipelineDeal}
          role="sponsor"
          isReviewed={Boolean(reviewedDeals[selectedPipelineDeal.id])}
          onClose={closePipelineDealModal}
          onOpenDetails={selectedPipelineDeal.deal_type === "sponsorship" ? () => openDealEventDetails(selectedPipelineDeal) : null}
          actions={{
            accept: !selectedPipelineDeal.sponsorAccepted
              ? () => handleDealAction(selectedPipelineDeal.id, acceptDeal, { role: "sponsor", accept: true })
              : null,
            pay:
              selectedPipelineDeal.status === "payment_pending" && !selectedPipelineDeal.paymentDone
                ? () => handleStartPayment(selectedPipelineDeal)
                : null,
            sign:
              selectedPipelineDeal.paymentDone && !selectedPipelineDeal.sponsorSigned
                ? () => handleStartSigning(selectedPipelineDeal)
                : null,
            review:
              selectedPipelineDeal.status === "closed" && !reviewedDeals[selectedPipelineDeal.id]
                ? () => {
                    setReviewDeal(selectedPipelineDeal);
                    setShowReviewModal(true);
                  }
                : null,
            agreement: selectedPipelineDeal.sponsorSigned ? () => setShowDocument({ type: "agreement", deal: selectedPipelineDeal }) : null,
            invoice: selectedPipelineDeal.paymentDone ? () => setShowDocument({ type: "invoice", deal: selectedPipelineDeal }) : null,
            chat: () => setActiveDealChat(selectedPipelineDeal),
          }}
          formatCurrency={formatCurrency}
        />
      )}

      {selectedEventDetails && (
        <EventDetailModal
          event={selectedEventDetails}
          deal={selectedEventDeal || deals.find(d => Number(d.event_id) === Number(selectedEventDetails.id))}
          onClose={() => {
            setSelectedEventDetails(null);
            setSelectedEventDeal(null);
          }}
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

