import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import ChatBox from "../components/ChatBox";
import DashboardStats from "../components/DashboardStats";
import EmptyState from "../components/EmptyState";
import DealCard from "../components/DealCard";
import MediaPortfolio from "../components/MediaPortfolio";
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
  deleteEvent,
  signDeal as signDealFn,
  updateEvent,
} from "../services/api";
import ReviewModal from "../components/ReviewModal";

const OrganizerDashboard = () => {
  const navigate = useNavigate();
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

  const [formData, setFormData] = useState({
    title: "", state: "Gujarat", city: "", budget: "", currency: "INR",
    category: "Tech", expected_audience: "", date: "", description: "", about: "",
    location: "",
  });
  const [currentUser] = useState(() => JSON.parse(localStorage.getItem("currentUser") || "{}"));
  const [searchTerm, setSearchTerm] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const loadData = async () => {
    try {
      const [sponsorsResp, eventsResp, dealsResp] = await Promise.all([
        getAvailableSponsors(),
        fetchEvents(),
        fetchDeals()
      ]);
      
      setAvailableSponsors(sponsorsResp
        .filter(u => !u.full_name?.toLowerCase().includes("test") && !u.company_name?.toLowerCase().includes("test"))
        .map(u => ({
          id: u.id,
          name: u.full_name || u.company_name || "Sponsor",
          focus: u.focus || "N/A",
          state: u.state || "N/A",
          city: u.city || "N/A",
          preferredBudget: u.preferred_budget ? `₹${Number(u.preferred_budget).toLocaleString("en-IN")}` : "N/A",
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
      } catch {}
    } catch (err) {}
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

    // Poll for deal updates every 30 s as a lightweight fallback.
    // Real-time updates are handled by the NotificationBell WebSocket (in Navbar).
    const pollInterval = setInterval(() => {
      refreshDeals();
    }, 30000);

    return () => clearInterval(pollInterval);
  }, [currentUser.id]);

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
      // toast shown by api interceptor
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
    } catch {
    } finally { setIsSubmitting(false); }
  };

  const handleConfirmDeleteEvent = async () => {
    try {
      await deleteEvent(eventToDelete);
      const resp = await fetchEvents();
      setEventsDay(resp.data);
    } catch {}
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
      toast.success("⭐ Review submitted! Thank you.");
      loadData();
    } catch {}
  };

  const handleAddMedia = async (eventId, mediaItem) => {
    const event = events.find(e => e.id === eventId);
    if (!event) return;
    const currentItems = event.media_items || [];
    try {
      await updateEvent(eventId, { media_items: [...currentItems, mediaItem] });
      toast.success("Media added!");
      loadData();
    } catch {}
  };

  const handleDeleteMedia = async (eventId, index) => {
    const event = events.find(e => e.id === eventId);
    if (!event) return;
    const updated = (event.media_items || []).filter((_, i) => i !== index);
    try {
      await updateEvent(eventId, { media_items: updated });
      toast.success("Media removed.");
      loadData();
    } catch {}
  };

  const stats = [
    { title: "Total Events", value: events.length },
    { title: "Active Deals", value: deals.filter(d => d.status !== "closed" && d.status !== "rejected").length },
    { title: "Revenue", value: formatCurrency(deals.filter(d => d.paymentDone).reduce((s, d) => s + (Number(d.paymentAmount) || 0), 0)) },
  ];

  return (
    <div>
      <Navbar role="organizer" />
      <div className="organizer-container">
        <header className="dashboard-header-horizontal">
          <div className="header-main-info">
            <div className="title-action-row">
              <h1 className="organizer-title">Organizer Command Center</h1>
              <button className="analytics-nav-btn" onClick={() => navigate('/analytics')}>
                📊 Analytics
              </button>
            </div>
            <p className="subtitle">Manage your events, deals, and partnerships in one place.</p>
          </div>
          <div className="header-actions">
            <button className="create-primary-btn" onClick={() => setIsCreateEventOpen(!isCreateEventOpen)}>
              {isCreateEventOpen ? "✕ Close Form" : "＋ Create New Event"}
            </button>
            <div className="header-filters">
              <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)} className="horizontal-select">
                {indianStates.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
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
                        <option value="INR">₹</option>
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

        <div className="horizontal-sections-stack">
          <section className="dashboard-section-wide">
            <div className="section-header">
              <h2>Active Deal Pipeline</h2>
              <span className="badge">{deals.length} Total</span>
            </div>
            <div className="horizontal-scroll-container">
              <div className="deal-pipeline-grid">
                {deals.filter(d => d.status !== 'rejected').map(deal => (
                  <DealCard key={deal.id} deal={deal}>
                    <div className="deal-card-content-wide">
                      <h4 className="deal-sponsor-name">
                        <span
                          className="profile-link"
                          onClick={() => navigate(`/profile/${deal.sponsor_id}`)}
                          title="View Sponsor Profile"
                        >
                          {deal.sponsorName}
                        </span>
                      </h4>
                      <div className="status-grid">
                        <span className={`status-pill ${deal.status}`}>{deal.status}</span>
                        <span className={`status-item ${deal.paymentDone ? 'done' : 'pending'}`}>
                          {deal.paymentDone ? '✅ Paid' : '⏳ Unpaid'}
                        </span>
                      </div>
                      <div className="deal-actions-row">
                        {!deal.organizerAccepted && (
                          <>
                            <button className="mini-action-btn primary" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "organizer", accept: true })}>Accept</button>
                            <button className="mini-action-btn reject" onClick={() => handleDealAction(deal.id, acceptDeal, { role: "organizer", accept: false })}>Reject</button>
                          </>
                        )}
                        {deal.paymentDone && !deal.organizerSigned && <button className="mini-action-btn legal" onClick={() => handleStartSigning(deal)}>Sign</button>}
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
                {deals.filter(d => d.status !== 'rejected').length === 0 && <EmptyState title="Quiet pipeline" description="Reach out to sponsors!" />}
              </div>
            </div>
          </section>

          <div className="dual-section-row">
            <section className="dashboard-section-wide marketplace-section">
              <div className="section-header marketplace-header-row">
                <div className="section-title-group">
                  <div className="title-with-action">
                    <h2>Discovery Marketplace</h2>
                    <button 
                      className={`filter-toggle-btn ${showFilters ? 'active' : ''}`}
                      onClick={() => setShowFilters(!showFilters)}
                    >
                      🔍 {showFilters ? 'Hide Filters' : 'Search & Filters'}
                    </button>
                  </div>
                  <p>Browse active sponsors matching your criteria.</p>
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
              <div className="sponsor-horizontal-grid">
                {availableSponsors.filter(s => {
                  const matchesState = selectedState === "All States" || s.state === selectedState;
                  const matchesSearch = 
                    s.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                    s.focus.toLowerCase().includes(searchTerm.toLowerCase()) ||
                    s.city.toLowerCase().includes(searchTerm.toLowerCase());
                  return matchesState && matchesSearch;
                }).map(s => (
                  <div key={s.id} className="sponsor-card-modern">
                    <div className="sponsor-badge">Sponsor</div>
                    <h3 className="sponsor-name">
                      <span 
                        style={{ cursor: 'pointer', textDecoration: 'underline dotted' }}
                        onClick={() => navigate(`/profile/${s.id}`)}
                      >{s.full_name || s.name}</span>
                    </h3>
                    <p className="sponsor-meta">{s.focus} • {s.city}</p>
                    <div className="sponsor-card-actions">
                      <button className="view-deal-btn" onClick={() => { setSelectedSponsor(s); setIsSponsorDetailsOpen(true); }}>Propose Partnership</button>
                      <button className="mini-profile-btn" onClick={() => navigate(`/profile/${s.id}`)}>👤 Profile</button>
                    </div>
                  </div>
                ))}
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
                        <span>📍 {e.city}</span>
                        <span className="divider">•</span>
                        <span>💰 {formatCurrency(e.budget, e.currency)}</span>
                        {(e.media_items?.length > 0) && <span className="media-badge">🖼️ {e.media_items.length} Photos</span>}
                      </div>
                    </div>
                    <div className="event-row-actions">
                      <button
                        className="media-toggle-btn"
                        onClick={() => setSelectedEventForMedia(selectedEventForMedia === e.id ? null : e.id)}
                        title="Manage Portfolio"
                      >
                        {selectedEventForMedia === e.id ? "✕ Gallery" : "🖼️ Gallery"}
                      </button>
                      <button className="delete-action-pill" onClick={() => { setEventToDelete(e.id); setIsDeleteDialogOpen(true); }} title="Remove Event">🗑️</button>
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
              title={`${ev.title} — Portfolio`}
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
        <div className="delete-dialog-overlay">
          <div className="delete-dialog glass-morphism">
            <div className="dialog-icon">🏢</div>
            <h3 className="dialog-title">Partner with {selectedSponsor.name}</h3>
            <p className="dialog-desc">Select an event you'd like to propose for sponsorship.</p>
            
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

            <div className="delete-dialog-actions">
              <button className="delete-cancel-btn" onClick={() => setIsSponsorDetailsOpen(false)}>Cancel</button>
              <button 
                className="delete-confirm-btn proposal-btn" 
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
                  } finally { setIsSubmitting(false); }
                }}
              >
                {isSubmitting ? "Sending..." : "Send Proposal"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OrganizerDashboard;