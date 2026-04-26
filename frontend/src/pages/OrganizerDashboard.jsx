import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import ChatBox from "../components/ChatBox";
import DashboardStats from "../components/DashboardStats";
import EmptyState from "../components/EmptyState";
import DealCard from "../components/DealCard";
import QuickActionsBar from "../components/QuickActionsBar";
import MediaPortfolio from "../components/MediaPortfolio";
import EventDetailModal from "../components/EventDetailModal";
import ActivityProgressModal from "../components/ActivityProgressModal";
import { formatCurrency } from "../utils/formatCurrency";
import { mapEventData, mapDealData } from "../utils/mapping";
import AgreementModal from "../components/AgreementModal";
import { INDIAN_STATES } from "../utils/constants";
import "./OrganizerDashboard.css";
import {
  acceptDeal,
  createReview,
  fetchMyReviews,
  createDeal,
  createEvent,
  fetchEvents,
  getAvailableSponsors,
  fetchDeals,
  fetchDeal,
  deleteEvent,
  signDeal as signDealFn,
  updateEvent,
} from "../services/api";
import ReviewModal from "../components/ReviewModal";
import DocumentViewer from "../components/DocumentViewer";

const logOrganizerError = (scope, err) => {
  console.error(`[OrganizerDashboard] ${scope}`, err);
};

const OrganizerDashboard = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const dealIdFromQuery = Number(searchParams.get("dealId") || 0);
  const indianStates = INDIAN_STATES;
  const categories = ["Tech", "Music", "Sports", "Business", "Education", "Art", "Social", "Other"];
  
  const [selectedState, setSelectedState] = useState("All States");
  const [events, setEvents] = useState([]);
  const [availableSponsors, setAvailableSponsors] = useState([]);
  const [deals, setDeals] = useState([]);
  const [reviewDrafts, setReviewDrafts] = useState({});
  const [isCreateEventOpen, setIsCreateEventOpen] = useState(false);
  const [selectedSponsor, setSelectedSponsor] = useState(null);
  const [isSponsorDetailsOpen, setIsSponsorDetailsOpen] = useState(false);
  const [eventToDelete, setEventToDelete] = useState(null);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeDealChat, setActiveDealChat] = useState(null);
  const [reviewDeal, setReviewDeal] = useState(null);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [reviewedDeals, setReviewedDeals] = useState({}); // { dealId: rating }
  const [selectedEventForMedia, setSelectedEventForMedia] = useState(null);
  const [selectedEventDetails, setSelectedEventDetails] = useState(null);
  const [selectedEventDeal, setSelectedEventDeal] = useState(null);
  const [selectedPipelineDeal, setSelectedPipelineDeal] = useState(null);

  const [formData, setFormData] = useState({
    title: "", state: "Gujarat", city: "", budget: "", currency: "INR",
    category: "Tech", expected_audience: "", date: "", description: "", about: "",
    location: "",
  });
  const [currentUser] = useState(() => JSON.parse(localStorage.getItem("currentUser") || "{}"));
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [showDocument, setShowDocument] = useState(null);

  const loadData = async () => {
    try {
      const eventParams = selectedState !== "All States" ? { state: selectedState } : {};
      
      const [sponsorsResp, eventsResp, dealsResp] = await Promise.all([
        getAvailableSponsors(),
        fetchEvents(eventParams),
        fetchDeals(),
      ]);
      
      setAvailableSponsors(sponsorsResp
        .map(u => ({
          id: u.id,
          name: u.full_name || u.company_name || "Sponsor",
          focus: u.focus || "N/A",
          state: u.state || "N/A",
          city: u.city || "N/A",
          preferredBudget: u.preferred_budget ? formatCurrency(Number(u.preferred_budget)) : "N/A",
          about: u.about || "N/A",
        })));

      setEventsDay(eventsResp.data);
      syncDeals(dealsResp.data);

      // Load past reviews so stars persist across page refreshes
      try {
        const myReviewsResp = await fetchMyReviews();
        const map = {};
        Object.entries(myReviewsResp.data || {}).forEach(([dealId, rating]) => {
          map[Number(dealId)] = rating;
        });
        setReviewedDeals(prev => ({ ...prev, ...map }));
      } catch (err) {
        logOrganizerError("failed to load review history", err);
      }
    } catch (err) {
      logOrganizerError("failed to load dashboard data", err);
    }
  };

  const setEventsDay = (rawEvents) => {
    setEvents(rawEvents.map(mapEventData));
  };

  const syncDeals = (rawDeals) => {
    const mine = rawDeals.filter(d => Number(d.organizer_id) === Number(currentUser.id));
    setDeals(mine.map(d => mapDealData(d, currentUser)));
  };

  const refreshDeals = async () => {
    const resp = await fetchDeals();
    syncDeals(resp.data);
  };

  useEffect(() => {
    loadData();

    // Global listener for real-time refreshes (triggered by WebSockets)
    const handleGlobalRefresh = () => {
      console.log("Real-time refresh triggered");
      loadData();
    };
    window.addEventListener('dashboard-refresh', handleGlobalRefresh);

    return () => {
      window.removeEventListener('dashboard-refresh', handleGlobalRefresh);
    };
  }, [currentUser.id, selectedState]); // Added selectedState as dependency

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentUser.id) {
      toast.error("User session expired. Please login again.");
      return;
    }
    
    setIsSubmitting(true);
    try {
      const budgetNum = parseFloat(formData.budget);
      const orgId = Number(currentUser.id);

      if (isNaN(orgId)) {
        toast.error("Invalid user session. Please re-login.");
        return;
      }
      
      const payload = {
        title: formData.title,
        description: formData.description || null,
        category: formData.category || "General",
        expected_audience: formData.expected_audience || null,
        about: formData.about || null,
        date: formData.date || null,
        location: formData.location || null,
        city: formData.city || null,
        state: formData.state || null,
        raw_budget: isNaN(budgetNum) ? 0 : budgetNum,
        currency: formData.currency || "INR",
        organizer_id: orgId,
      };

      console.log("Sending Event Payload:", payload);
      
      await createEvent(payload);
      const resp = await fetchEvents();
      setEventsDay(resp.data);
      setFormData({ 
        title: "", state: "Gujarat", city: "", budget: "", currency: "INR", 
        category: "Tech", expected_audience: "", date: "", description: "", about: "",
        location: "",
      });
      setIsCreateEventOpen(false);
      toast.success("Event Published!");
    } catch (err) {
      // Toast may already be shown by API interceptor.
      logOrganizerError("failed to create event", err);
    } finally { setIsSubmitting(false); }
  };

  const handleDealAction = async (dealId, actionFn, payload) => {
    setIsSubmitting(true);
    try {
      if (payload.accept === false) {
        if (!window.confirm("Are you sure you want to reject this deal?")) return;
      }
      await actionFn(dealId, payload);
      await refreshDeals();
      toast.success("Pipeline Updated");
    } catch (err) {
      logOrganizerError("failed to update deal action", err);
      toast.error("Unable to update deal right now.");
    } finally { setIsSubmitting(false); }
  };

  const handleConfirmDeleteEvent = async () => {
    try {
      await deleteEvent(eventToDelete);
      const resp = await fetchEvents();
      setEventsDay(resp.data);
    } catch (err) {
      logOrganizerError("failed to delete event", err);
      toast.error("Unable to delete event.");
    }
    setIsDeleteDialogOpen(false);
  };

  const [signDeal, setSignDeal] = useState(null);
  const [showAgreementModal, setShowAgreementModal] = useState(false);

  const handleStartSigning = (deal) => {
    setSignDeal({ ...deal, content: `AGREEMENT\n${deal.organizerName} & ${deal.sponsorName}\nAmount: ${deal.paymentAmount}` });
    setShowAgreementModal(true);
  };

  const handleSignSuccess = (signature) => {
    handleDealAction(signDeal.id, signDealFn, { role: "organizer", signature });
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
      toast.success("Review submitted! Thank you.");
      loadData();
    } catch (err) {
      logOrganizerError("failed to submit review", err);
      toast.error("Unable to submit review.");
    }
  };

  const getDealPartnerName = (deal) => deal.sponsorName || "Sponsor";
  const getDealSubject = (deal) => deal.event?.title || "Event sponsorship";
  const getDealSubline = (deal) => {
    const city = deal.event?.city || deal.event?.location || "Location TBD";
    return `${city} - Sponsorship Deal`;
  };
  const getDealValue = (deal) =>
    Number(deal.paymentAmount) || Number(deal.event?.raw_budget) || Number(deal.event?.budget) || 0;

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
    const fromEventList = events.find((evt) => Number(evt.id) === Number(deal?.event_id));
    const eventForModal = fromDealPayload || fromEventList || null;
    if (!eventForModal) {
      toast.error("Event details are unavailable for this deal.");
      return;
    }
    setSelectedEventDetails(eventForModal);
    setSelectedEventDeal(deal);
  };

  const handleAddMedia = async (eventId, mediaItem) => {
    const event = events.find(e => e.id === eventId);
    if (!event) return;
    const currentItems = event.media_items || [];
    try {
      await updateEvent(eventId, { media_items: [...currentItems, mediaItem] });
      toast.success("Media added!");
      loadData();
    } catch (err) {
      logOrganizerError(`failed to add media for event #${eventId}`, err);
      toast.error("Unable to add media.");
    }
  };

  const handleDeleteMedia = async (eventId, index) => {
    const event = events.find(e => e.id === eventId);
    if (!event) return;
    const updated = (event.media_items || []).filter((_, i) => i !== index);
    try {
      await updateEvent(eventId, { media_items: updated });
      toast.success("Media removed.");
      loadData();
    } catch (err) {
      logOrganizerError(`failed to delete media for event #${eventId}`, err);
      toast.error("Unable to remove media.");
    }
  };

  const stats = [
    { title: "Total Events", value: events.length },
    { title: "Active Deals", value: deals.filter(d => d.status !== "closed" && d.status !== "rejected").length },
    { title: "Revenue", value: formatCurrency(deals.filter(d => d.paymentDone).reduce((s, d) => s + (Number(d.paymentAmount) || 0), 0)) },
  ];

  const getLatestItems = (items, count = 4) =>
    [...items]
      .sort((a, b) => Number(b?.id || 0) - Number(a?.id || 0))
      .slice(0, count);

  const visiblePipelineDeals = deals.filter((deal) => deal.status !== "rejected");

  const filteredSponsors = availableSponsors.filter((sponsor) => {
    const matchesState = selectedState === "All States" || sponsor.state === selectedState;
    const matchesSearch =
      sponsor.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sponsor.focus.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sponsor.city.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesState && matchesSearch;
  });

  const latestPipelineDeals = getLatestItems(visiblePipelineDeals);
  const latestSponsors = getLatestItems(filteredSponsors);

  const quickActions = [
    { key: "create", label: "Create Event", tone: "primary", onClick: () => setIsCreateEventOpen(true) },
    { key: "ops", label: "Scale Ops", tone: "emphasis", onClick: () => navigate("/scale-ops") },
    { key: "analytics", label: "Analytics", onClick: () => navigate("/analytics") },
    { key: "profile", label: "Profile", onClick: () => navigate("/my-profile") },
  ];

  const openDealProgress = (deal) => {
    const dealId = Number(deal?.id || 0);
    if (!dealId) return;
    fetchDeal(dealId)
      .then((resp) => {
        const fresh = mapDealData(resp.data, currentUser);
        setSelectedPipelineDeal(fresh);
      })
      .catch((err) => {
        logOrganizerError(`failed to refresh deal #${dealId} details`, err);
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
    navigate(`/activity-center?section=${section}`);
  };

  return (
    <div>
      <Navbar role="organizer" />
      <div className="organizer-container">
        <header className="dashboard-header-horizontal">
          <div className="header-main-info">
            <div className="title-action-row">
              <h1 className="organizer-title">Organizer Dashboard</h1>
              <button className="analytics-nav-btn" onClick={() => navigate('/analytics')}>
                Analytics
              </button>
            </div>
            <p className="subtitle">Manage events, sponsors, and signed deals in one place.</p>
          </div>
          <div className="header-actions">
            <button className="create-primary-btn" onClick={() => setIsCreateEventOpen(!isCreateEventOpen)}>
              {isCreateEventOpen ? "Close Form" : "+ Create New Event"}
            </button>
          </div>
        </header>

        {isCreateEventOpen && (
          <div className="create-event-overlay-horizontal">
            <div className="create-event-card-horizontal">
              <form className="horizontal-event-form" onSubmit={handleSubmit}>
                <div className="form-grid">
                  <div className="form-group">
                    <label>Event Name</label>
                    <input name="title" placeholder="e.g. Tech Spark 2024" required value={formData.title} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Category</label>
                    <select name="category" value={formData.category} onChange={handleChange}>
                      {categories.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Date</label>
                    <input type="date" name="date" value={formData.date} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Expected Audience</label>
                    <input name="expected_audience" placeholder="e.g. 500+ Students" value={formData.expected_audience} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>State</label>
                    <select name="state" value={formData.state} onChange={handleChange}>
                      {indianStates.filter(s => s !== "All States").map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>City</label>
                    <input name="city" placeholder="City" required value={formData.city} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Venue / Detailed Location</label>
                    <input name="location" placeholder="e.g. Science City, Ahmedabad" value={formData.location} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label>Budget Needed</label>
                    <div className="budget-input-group">
                      <select name="currency" value={formData.currency} onChange={handleChange}>
                        <option value="INR">INR</option>
                        <option value="USD">$</option>
                      </select>
                      <input type="number" name="budget" placeholder="0" required value={formData.budget} onChange={handleChange} />
                    </div>
                  </div>
                  <div className="form-group full-width">
                    <label>Short Catchy Description (For Cards)</label>
                    <textarea name="description" placeholder="A brief one-liner summary..." value={formData.description} onChange={handleChange} rows="1" />
                  </div>
                  <div className="form-group full-width">
                    <label>Detailed About Event</label>
                    <textarea name="about" placeholder="Tell sponsors more about the event, highlights, and benefits..." value={formData.about} onChange={handleChange} rows="3" />
                  </div>
                </div>
                <div className="form-actions">
                  <button type="submit" className="publish-btn-wide" disabled={isSubmitting}>
                    {isSubmitting ? "Processing..." : "Publish Event"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        <DashboardStats stats={stats} />
        <QuickActionsBar actions={quickActions} />
        <div className="horizontal-sections-stack">
          <section className="dashboard-section-wide">
            <div className="section-header">
              <h2>
                <button type="button" className="section-nav-link" onClick={() => goToActivityCenter("pipeline")}>
                  Active Deal Pipeline
                </button>
              </h2>
              <span className="badge">{visiblePipelineDeals.length} Total</span>
            </div>
            <div className="horizontal-scroll-container">
              <div className="deal-pipeline-grid h-scroll-grid">
                {latestPipelineDeals.map(deal => (
                  <DealCard key={deal.id} deal={deal}>
                    <div className="deal-card-content-wide">
                      <div className="pipeline-card-head">
                        <div className="deal-type-chip">Event Deal</div>
                        <h4 className="deal-sponsor-name">
                          <span
                            className="profile-link"
                            onClick={() => navigate(`/profile/${deal.sponsor_id}`)}
                            title="View Sponsor Profile"
                          >
                            {getDealPartnerName(deal)}
                          </span>
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
                        <span className="deal-meta-item">Value: {formatCurrency(getDealValue(deal))}</span>
                        <span className="deal-meta-item">ID: #{deal.id}</span>
                      </div>
                      <div className="status-grid">
                        <span className={`status-pill ${deal.status}`}>{deal.status}</span>
                        <span className={`status-item ${deal.paymentDone ? 'done' : 'pending'}`}>
                          {deal.paymentDone ? "Paid" : "Payment Pending"}
                        </span>
                      </div>
                      <div className="deal-actions-row">
                        {!deal.organizerAccepted && (
                          <>
                            <button className="mini-action-btn primary" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "organizer", accept: true })}>Accept</button>
                            <button className="mini-action-btn reject" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "organizer", accept: false })}>Reject</button>
                          </>
                        )}
                        {deal.status === "closed" ? (
                          reviewedDeals[deal.id] ? (
                            <div className="reviewed-badge">
                              {Array.from({ length: 5 }, (_, i) => (
                                <span key={i} className={i < reviewedDeals[deal.id] ? "rstar filled" : "rstar"}>*</span>
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
                            disabled={!deal.paymentDone || deal.organizerSigned}
                            onClick={() => deal.paymentDone && !deal.organizerSigned && handleStartSigning(deal)}
                          >
                            Sign
                          </button>
                        )}
                      </div>
                      <div className="pipeline-main-actions">
                        <button
                          className="mini-action-btn legal-outline"
                          disabled={!deal.organizerSigned}
                          onClick={() => deal.organizerSigned && setShowDocument({ type: "agreement", deal })}
                        >
                          Agreement
                        </button>
                        <button
                          className="mini-action-btn primary-outline invoice-btn"
                          disabled={!deal.paymentDone}
                          onClick={() => deal.paymentDone && setShowDocument({ type: "invoice", deal })}
                        >
                          Invoice
                        </button>
                        <button className="mini-action-btn chat" onClick={() => setActiveDealChat(deal)}>Chat</button>
                      </div>
                    </div>
                  </DealCard>
                ))}
                {visiblePipelineDeals.length === 0 && (
                  <EmptyState
                    title="No active deals yet"
                    description="Start by sending your first sponsorship proposal."
                    actionLabel="Open Marketplace"
                    onAction={() => setShowFilters(true)}
                  />
                )}
              </div>
            </div>
          </section>

          <div className="dual-section-row">
            <section className="dashboard-section-wide marketplace-section">
              <div className="section-header marketplace-header-row">
                <div className="section-title-group">
                  <div className="title-with-action">
                    <h2>
                      <button type="button" className="section-nav-link" onClick={() => goToActivityCenter("discovery")}>
                        Discovery Marketplace
                      </button>
                    </h2>
                    <button 
                      className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
                      onClick={() => setShowFilters(!showFilters)}
                    >
                      {showFilters ? "Hide Advanced" : "Advanced Filters"}
                    </button>
                  </div>
                  <p>Browse active sponsors using your selected criteria.</p>
                </div>

                {showFilters && (
                  <div className="marketplace-filters-bar glass-morphism animate-in">
                    <input 
                      type="text" 
                      placeholder="Search sponsors by name, focus, city..." 
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="search-input"
                    />
                    <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)} className="filter-select">
                      {indianStates.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                )}
              </div>
              <div className="sponsor-horizontal-grid h-scroll-grid">
                {latestSponsors.map(s => (
                  <div key={s.id} className="sponsor-card-modern">
                    <div className="sponsor-badge">Sponsor</div>
                    <h3 className="sponsor-name">
                      <span 
                        style={{ cursor: 'pointer', textDecoration: 'underline dotted' }}
                        onClick={() => navigate(`/profile/${s.id}`)}
                      >{s.full_name || s.name}</span>
                    </h3>
                    <p className="sponsor-meta">{s.focus} | {s.city}</p>
                    <div className="sponsor-card-actions">
                      <button className="view-deal-btn" onClick={() => { setSelectedSponsor(s); setIsSponsorDetailsOpen(true); }}>Propose Partnership</button>
                      <button className="mini-profile-btn" onClick={() => navigate(`/profile/${s.id}`)}>Profile</button>
                    </div>
                  </div>
                ))}
                {filteredSponsors.length === 0 && (
                  <EmptyState
                    title="No sponsors match these filters"
                    description="Try broadening state or search terms."
                    actionLabel="Clear Filters"
                    onAction={() => {
                      setSearchTerm("");
                      setSelectedState("All States");
                    }}
                  />
                )}
              </div>
            </section>
            <section className="dashboard-section-wide management-section">
              <div className="section-header">
                <h2>Your Global Events</h2>
              </div>
              <div className="events-list-compact">
                {events.filter(e => Number(e.organizer_id) === Number(currentUser.id)).map(e => (
                  <div key={e.id} className="event-row-modern">
                    <div className="event-row-info">
                      <h4>{e.title}</h4>
                      <div className="event-row-meta">
                        <span>Location: {e.city}</span>
                        <span className="divider">|</span>
                        <span>Budget: {formatCurrency(e.budget, e.currency)}</span>
                        {(e.media_items?.length > 0) && <span className="media-badge">{e.media_items.length} Photos</span>}
                      </div>
                    </div>
                    <div className="event-row-actions">
                      <button
                        className="media-toggle-btn"
                        onClick={() => setSelectedEventForMedia(selectedEventForMedia === e.id ? null : e.id)}
                        title="Manage Portfolio"
                      >
                        {selectedEventForMedia === e.id ? "Close Gallery" : "Gallery"}
                      </button>
                      <button
                        className="delete-action-pill"
                        onClick={() => { setEventToDelete(e.id); setIsDeleteDialogOpen(true); }}
                        title="Remove Event"
                        aria-label="Delete event"
                      >
                        <span className="trash-icon" aria-hidden="true">🗑</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </div>

        {/* Media Portfolio for selected event */}
        {selectedEventForMedia && (() => {
          const ev = events.find(e => e.id === selectedEventForMedia);
          return ev ? (
            <MediaPortfolio
              items={ev.media_items || []}
              title={`${ev.title} - Portfolio`}
              canEdit={Number(ev.organizer_id) === Number(currentUser.id)}
              onAdd={(item) => handleAddMedia(ev.id, item)}
              onDelete={(idx) => handleDeleteMedia(ev.id, idx)}
            />
          ) : null;
        })()}
      </div>

      {showAgreementModal && <AgreementModal deal={signDeal} role="organizer" onSign={handleSignSuccess} onClose={() => setShowAgreementModal(false)} />}
      {showReviewModal && (
        <ReviewModal 
          deal={reviewDeal} 
          reviewerRole="organizer" 
          targetRole="sponsor" 
          onSubmit={handleReviewSubmit} 
          onClose={() => setShowReviewModal(false)} 
        />
      )}
      {activeDealChat && <ChatBox role="organizer" title={`Chat: ${activeDealChat.sponsorName}`} chatKey={`deal_${activeDealChat.id}`} onClose={() => setActiveDealChat(null)} />}
      {isDeleteDialogOpen && (
        <div className="delete-dialog-overlay">
          <div className="delete-dialog">
            <h3>Permanently Delete?</h3>
            <p>This action cannot be undone. All active connections for this event will be closed.</p>
            <div className="delete-dialog-actions">
              <button className="delete-cancel-btn" onClick={() => setIsDeleteDialogOpen(false)}>Cancel</button>
              <button className="delete-confirm-btn" onClick={handleConfirmDeleteEvent}>Yes, Delete</button>
            </div>
          </div>
        </div>
      )}
      {isSponsorDetailsOpen && selectedSponsor && (
        <div className="proposal-modal-overlay" onClick={() => setIsSponsorDetailsOpen(false)}>
          <div className="proposal-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="proposal-modal-icon">{"\uD83E\uDD1D"}</div>
            <h3 className="proposal-modal-title">Partner with {selectedSponsor.name}</h3>
            <p className="proposal-modal-desc">Select an event you'd like to propose for sponsorship.</p>

            <div className="event-selector-list">
              {events.filter(e => Number(e.organizer_id) === Number(currentUser.id)).map(e => (
                <div
                  key={e.id}
                  className={`selector-item ${formData.event_id === e.id ? 'active' : ''}`}
                  onClick={() => setFormData({ ...formData, event_id: e.id })}
                >
                  <span className="selector-name">{e.title}</span>
                  <span className="selector-budget">{formatCurrency(e.budget)}</span>
                </div>
              ))}
              {events.filter(e => Number(e.organizer_id) === Number(currentUser.id)).length === 0 && (
                <p className="empty-text-mini">You need to create an event first.</p>
              )}
            </div>

            <div className="proposal-modal-actions">
              <button className="proposal-cancel-btn" onClick={() => setIsSponsorDetailsOpen(false)}>Cancel</button>
              <button
                className="proposal-confirm-btn"
                disabled={!formData.event_id || isSubmitting}
                onClick={async () => {
                  setIsSubmitting(true);
                  try {
                    await createDeal({
                      sponsor_id: selectedSponsor.id,
                      organizer_id: currentUser.id,
                      event_id: formData.event_id,
                      deal_type: "sponsorship"
                    });
                    await refreshDeals();
                    setIsSponsorDetailsOpen(false);
                    toast.success("Partnership Proposal Sent!");
                  } catch (err) {
                    logOrganizerError("failed to send sponsor proposal", err);
                    toast.error("Unable to send proposal.");
                  } finally { setIsSubmitting(false); }
                }}
              >
                {isSubmitting ? "Sending..." : "Send Proposal"}
              </button>
            </div>
          </div>
        </div>
      )}
      {showDocument && (
        <DocumentViewer 
            type={showDocument.type} 
            deal={showDocument.deal} 
            onClose={() => setShowDocument(null)} 
        />
      )}
      {selectedPipelineDeal && (
        <ActivityProgressModal
          deal={selectedPipelineDeal}
          role="organizer"
          isReviewed={Boolean(reviewedDeals[selectedPipelineDeal.id])}
          onClose={closePipelineDealModal}
          onOpenDetails={() => openDealEventDetails(selectedPipelineDeal)}
          actions={{
            accept: !selectedPipelineDeal.organizerAccepted
              ? () => handleDealAction(selectedPipelineDeal.id, acceptDeal, { role: "organizer", accept: true })
              : null,
            sign:
              selectedPipelineDeal.paymentDone && !selectedPipelineDeal.organizerSigned
                ? () => handleStartSigning(selectedPipelineDeal)
                : null,
            review:
              selectedPipelineDeal.status === "closed" && !reviewedDeals[selectedPipelineDeal.id]
                ? () => {
                    setReviewDeal(selectedPipelineDeal);
                    setShowReviewModal(true);
                  }
                : null,
            agreement: selectedPipelineDeal.organizerSigned ? () => setShowDocument({ type: "agreement", deal: selectedPipelineDeal }) : null,
            invoice: selectedPipelineDeal.paymentDone ? () => setShowDocument({ type: "invoice", deal: selectedPipelineDeal }) : null,
            chat: () => setActiveDealChat(selectedPipelineDeal),
          }}
          formatCurrency={formatCurrency}
        />
      )}
      {selectedEventDetails && (
        <EventDetailModal
          event={selectedEventDetails}
          deal={selectedEventDeal}
          onClose={() => {
            setSelectedEventDetails(null);
            setSelectedEventDeal(null);
          }}
          onProposeDeal={() => {}}
          onChat={setActiveDealChat}
          formatCurrency={formatCurrency}
        />
      )}
    </div>
  );
};

export default OrganizerDashboard;
