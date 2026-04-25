import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";
import Navbar from "../components/Navbar";
import EmptyState from "../components/EmptyState";
import DealCard from "../components/DealCard";
import ChatBox from "../components/ChatBox";
import PaymentModal from "../components/PaymentModal";
import AgreementModal from "../components/AgreementModal";
import ReviewModal from "../components/ReviewModal";
import DocumentViewer from "../components/DocumentViewer";
import EventDetailModal from "../components/EventDetailModal";
import ActivityProgressModal from "../components/ActivityProgressModal";
import { formatCurrency } from "../utils/formatCurrency";
import { mapDealData, mapEventData } from "../utils/mapping";
import {
  acceptDeal,
  createPaymentOrder,
  createReview,
  fetchCampaigns,
  fetchDeal,
  fetchDeals,
  fetchEvents,
  fetchMyReviews,
  fetchPaymentCheckoutConfig,
  getAvailableInfluencers,
  getAvailableSponsors,
  verifyPayment,
  signDeal as signDealFn,
} from "../services/api";
import "./ActivityCenterPage.css";

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

const getDashboardPath = (role) => {
  if (role === "sponsor") return "/sponsor-dashboard";
  if (role === "organizer") return "/organizer-dashboard";
  return "/influencer-dashboard";
};

const getSectionLabel = (section, role, pipeline) => {
  if (section === "pipeline") return role === "influencer" ? "My Brand Pipeline" : "Active Pipeline";
  if (section === "events") return "Event Marketplace";
  if (section === "discovery") {
    if (role === "sponsor" && pipeline === "influencers") return "Creator Discovery";
    return "Discovery Marketplace";
  }
  if (section === "opportunities") return "Brand Opportunities";
  return "Activity Center";
};

const getReviewTargetRole = (role, dealType) => {
  if (role === "sponsor") return dealType === "sponsorship" ? "organizer" : "influencer";
  return "sponsor";
};

const getChatPartnerName = (deal, role) => {
  if (!deal) return "Partner";
  if (role === "sponsor") {
    return deal.deal_type === "sponsorship"
      ? deal.organizerName || "Organizer"
      : deal.influencerName || "Creator";
  }
  return deal.sponsorName || "Sponsor";
};

const ActivityCenterPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchInput, setSearchInput] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [autoOpenedDealId, setAutoOpenedDealId] = useState(null);
  const [reviewedDeals, setReviewedDeals] = useState({});
  const [reviewDeal, setReviewDeal] = useState(null);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [paymentDeal, setPaymentDeal] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [signDeal, setSignDeal] = useState(null);
  const [showAgreementModal, setShowAgreementModal] = useState(false);
  const [showDocument, setShowDocument] = useState(null);
  const [activeDealChat, setActiveDealChat] = useState(null);
  const [selectedEventDetails, setSelectedEventDetails] = useState(null);
  const [selectedEventDeal, setSelectedEventDeal] = useState(null);

  const currentUser = JSON.parse(localStorage.getItem("currentUser") || "{}");
  const role = (currentUser.role || "").toLowerCase();
  const section = (searchParams.get("section") || "pipeline").toLowerCase();
  const pipeline = (searchParams.get("pipeline") || "events").toLowerCase();
  const dealIdFromQuery = Number(searchParams.get("dealId") || 0);
  const dashboardPath = getDashboardPath(role);

  const loadData = async () => {
    if (!currentUser?.id) return;
    setIsLoading(true);
    try {
      if (section === "pipeline") {
        const dealsResp = await fetchDeals();
        let mine = [];
        if (role === "sponsor") mine = dealsResp.data.filter((deal) => Number(deal.sponsor_id) === Number(currentUser.id));
        if (role === "organizer") mine = dealsResp.data.filter((deal) => Number(deal.organizer_id) === Number(currentUser.id));
        if (role === "influencer") mine = dealsResp.data.filter((deal) => Number(deal.influencer_id) === Number(currentUser.id));
        if (role === "sponsor" && pipeline === "events") mine = mine.filter((deal) => deal.deal_type === "sponsorship");
        if (role === "sponsor" && pipeline === "influencers") mine = mine.filter((deal) => deal.deal_type === "promotion");
        const mapped = mine.map((deal) => mapDealData(deal, currentUser));
        setItems(mapped.sort((a, b) => Number(b.id || 0) - Number(a.id || 0)));
      } else if (section === "events") {
        const eventsResp = await fetchEvents();
        const mapped = eventsResp.data.map(mapEventData);
        setItems(mapped.sort((a, b) => Number(b.id || 0) - Number(a.id || 0)));
      } else if (section === "discovery") {
        if (role === "organizer") {
          const sponsors = await getAvailableSponsors();
          const mapped = sponsors.map((user) => ({
            id: user.id,
            name: user.full_name || user.company_name || "Sponsor",
            focus: user.focus || "N/A",
            city: user.city || "N/A",
            state: user.state || "N/A",
          }));
          setItems(mapped.sort((a, b) => Number(b.id || 0) - Number(a.id || 0)));
        } else {
          const influencers = await getAvailableInfluencers();
          const mapped = influencers.map((user) => ({
            id: user.id,
            name: user.full_name || "Creator",
            niche: user.niche || "General",
            audience: Number(user.audience_size) || 0,
            platforms: user.platforms || "Social Media",
          }));
          setItems(mapped.sort((a, b) => Number(b.id || 0) - Number(a.id || 0)));
        }
      } else if (section === "opportunities") {
        const campaignsResp = await fetchCampaigns();
        setItems((campaignsResp.data || []).sort((a, b) => Number(b.id || 0) - Number(a.id || 0)));
      } else {
        setItems([]);
      }

      try {
        const myReviewsResp = await fetchMyReviews();
        const map = {};
        Object.entries(myReviewsResp.data || {}).forEach(([id, rating]) => {
          map[Number(id)] = rating;
        });
        setReviewedDeals(map);
      } catch {
        setReviewedDeals({});
      }
    } catch {
      toast.error("Unable to load activities.");
    } finally {
      setIsLoading(false);
    }
  };

  const openPipelineDeal = async (dealOrId) => {
    const id = Number(typeof dealOrId === "number" ? dealOrId : dealOrId?.id);
    if (!id) return;
    const fallbackDeal =
      typeof dealOrId === "object"
        ? dealOrId
        : items.find((deal) => Number(deal.id) === id) || null;

    try {
      const freshResp = await fetchDeal(id);
      setSelectedDeal(mapDealData(freshResp.data, currentUser));
    } catch {
      if (fallbackDeal) {
        setSelectedDeal(fallbackDeal);
      } else {
        toast.error("Unable to open latest deal data.");
      }
    }
  };

  const handleDealAction = async (dealId, actionFn, payload, successMsg = "Deal updated.") => {
    try {
      await actionFn(dealId, payload);
      toast.success(successMsg);
      await loadData();
      await openPipelineDeal(dealId);
    } catch {
      toast.error("Unable to complete this action right now.");
    }
  };

  const handleStartPayment = (deal) => {
    const resolvedAmount =
      Number(deal.paymentAmount) ||
      Number(deal.event?.raw_budget) ||
      Number(deal.event?.budget) ||
      Number(deal.campaign?.budget) ||
      0;

    if (!Number.isFinite(resolvedAmount) || resolvedAmount <= 0) {
      toast.error("Deal amount is not configured yet. Please refresh or contact support.");
      return;
    }
    setPaymentDeal({ ...deal, paymentAmount: resolvedAmount });
    setShowPaymentModal(true);
  };

  const handlePaymentSuccess = async () => {
    if (!paymentDeal?.id) return;
    try {
      const [orderResp, configResp] = await Promise.all([
        createPaymentOrder(paymentDeal.id, { forceNew: true }),
        fetchPaymentCheckoutConfig(),
      ]);

      const orderData = orderResp?.data || {};
      const orderId = orderData.razorpay_payment_id;
      const keyId = configResp?.data?.key_id;
      const amountPaise = Math.round(Number(orderData.payment_amount || paymentDeal.paymentAmount || 0) * 100);
      const currency = orderData.currency || paymentDeal.currency || "INR";

      if (!keyId) {
        toast.error("Payment gateway key is missing. Set RAZORPAY_KEY_ID in backend environment.");
        return;
      }
      if (!orderId) {
        toast.error("Payment order was not created. Please try again.");
        return;
      }
      if (amountPaise <= 0) {
        toast.error("Invalid payment amount for this deal. Please refresh and retry.");
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
        handler: async (gatewayPayload) => {
          try {
            await verifyPayment({
              deal_id: paymentDeal.id,
              razorpay_order_id: gatewayPayload?.razorpay_order_id || orderId,
              razorpay_payment_id: gatewayPayload?.razorpay_payment_id,
              razorpay_signature: gatewayPayload?.razorpay_signature,
            });
            toast.success("Payment verified and pipeline updated.");
            await loadData();
            await openPipelineDeal(paymentDeal.id);
          } catch (verifyError) {
            const verifyMessage =
              verifyError?.response?.data?.message ||
              verifyError?.response?.data?.detail ||
              "Payment authorized, but verification failed. Please refresh and retry.";
            toast.error(verifyMessage);
          }
        },
        modal: {
          ondismiss: () => {
            toast("Checkout closed. You can retry payment anytime.");
          },
        },
        prefill: {
          name: currentUser.full_name || currentUser.company_name || "Sponsor",
          email: currentUser.email || "",
          contact: currentUser.phone || "",
        },
        theme: {
          color: "#f97316",
        },
      });

      rzp.on("payment.failed", (response) => {
        const gatewayMessage =
          response?.error?.description ||
          response?.error?.reason ||
          response?.error?.source ||
          "Payment failed. Please try again.";
        toast.error(gatewayMessage);
      });

      rzp.open();
    } catch (error) {
      const apiMessage =
        error?.response?.data?.message ||
        error?.response?.data?.detail ||
        error?.message ||
        "Unable to open payment gateway. Please try again.";
      toast.error(apiMessage);
    }
  };

  const handleStartSigning = (deal) => {
    if (deal.deal_type === "sponsorship") {
      setSignDeal({
        ...deal,
        content: `AGREEMENT\n${deal.organizerName} & ${deal.sponsorName}\nAmount: ${deal.paymentAmount}`,
      });
    } else {
      setSignDeal({
        ...deal,
        content: `CAMPAIGN PARTNERSHIP AGREEMENT\nBetween ${deal.sponsorName} and ${deal.influencerName}\nCampaign: ${deal.campaign?.title}\nPayment: ${deal.paymentAmount} ${deal.currency}`,
      });
    }
    setShowAgreementModal(true);
  };

  const handleSignSuccess = async (signature) => {
    if (!signDeal?.id) return;
    try {
      await signDealFn(signDeal.id, { role, signature });
      toast.success("Agreement signed successfully.");
      setShowAgreementModal(false);
      setSignDeal(null);
      await loadData();
      await openPipelineDeal(signDeal.id);
    } catch {
      toast.error("Unable to submit signature.");
    }
  };

  const handleReviewSubmit = async (reviewData) => {
    try {
      await createReview({
        ...reviewData,
        reviewer_id: currentUser.id,
      });
      setReviewedDeals((prev) => ({ ...prev, [reviewDeal.id]: reviewData.rating }));
      setShowReviewModal(false);
      setReviewDeal(null);
      toast.success("Review submitted. Thank you.");
      await loadData();
    } catch {
      toast.error("Unable to submit review.");
    }
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
    const eventForModal = normalizeEventForModal(deal?.event, deal?.organizer_id);
    if (!eventForModal) {
      toast.error("Event details are unavailable for this deal.");
      return;
    }
    setSelectedEventDetails(eventForModal);
    setSelectedEventDeal(deal);
  };

  useEffect(() => {
    loadData();
  }, [currentUser?.id, pipeline, role, section]);

  useEffect(() => {
    if (section !== "pipeline") return;
    if (!dealIdFromQuery || isLoading) return;
    if (autoOpenedDealId === dealIdFromQuery) return;
    setAutoOpenedDealId(dealIdFromQuery);
    openPipelineDeal(dealIdFromQuery);
  }, [autoOpenedDealId, dealIdFromQuery, isLoading, section, items]);

  useEffect(() => {
    if (!dealIdFromQuery) {
      setAutoOpenedDealId(null);
    }
  }, [dealIdFromQuery]);

  const applySearch = (event) => {
    event.preventDefault();
    setSearchTerm(searchInput.trim().toLowerCase());
  };

  const filteredItems = useMemo(() => {
    if (!searchTerm) return items;
    return items.filter((item) => {
      if (section === "pipeline") {
        const subject = item.deal_type === "sponsorship" ? item.event?.title || "" : item.campaign?.title || "";
        const partner = role === "sponsor"
          ? (item.deal_type === "sponsorship" ? item.organizerName : item.influencerName)
          : item.sponsorName;
        const haystack = `${subject} ${partner || ""} ${item.status || ""} ${item.id || ""}`.toLowerCase();
        return haystack.includes(searchTerm);
      }
      if (section === "events") {
        const haystack = `${item.title || ""} ${item.city || ""} ${item.category || ""}`.toLowerCase();
        return haystack.includes(searchTerm);
      }
      if (section === "opportunities") {
        const haystack = `${item.title || ""} ${item.description || ""} ${item.platform_required || ""}`.toLowerCase();
        return haystack.includes(searchTerm);
      }
      const haystack = `${item.name || ""} ${item.focus || ""} ${item.niche || ""} ${item.city || ""}`.toLowerCase();
      return haystack.includes(searchTerm);
    });
  }, [items, role, searchTerm, section]);

  const sectionLabel = getSectionLabel(section, role, pipeline);

  return (
    <div>
      <Navbar role={role || "sponsor"} />
      <div className="activity-center-container">
        <header className="activity-center-header">
          <button type="button" className="activity-center-back-btn" onClick={() => navigate(dashboardPath)}>
            Back to Dashboard
          </button>
          <h1>{sectionLabel}</h1>
          <p>Search and manage full activity history from one place.</p>
        </header>

        <form className="activity-center-search-row" onSubmit={applySearch}>
          <input
            type="text"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder={`Search in ${sectionLabel.toLowerCase()}...`}
          />
          <button type="submit">Search</button>
        </form>

        <section className="activity-center-list-wrap">
          <div className="activity-center-list-header">
            <h2>{sectionLabel}</h2>
            <span className="badge">{filteredItems.length} Results</span>
          </div>

          {isLoading ? (
            <div className="activity-center-loading">Loading activities...</div>
          ) : filteredItems.length === 0 ? (
            <EmptyState
              title="No activities found"
              description="Try another keyword or clear the current search."
              actionLabel="Clear Search"
              onAction={() => {
                setSearchInput("");
                setSearchTerm("");
              }}
            />
          ) : (
            <div className="activity-center-grid">
              {section === "pipeline" && filteredItems.map((deal) => (
                <DealCard key={deal.id} deal={deal}>
                  <button type="button" className="activity-center-deal-btn" onClick={() => openPipelineDeal(deal)}>
                    <span className="activity-center-chip">{deal.deal_type === "sponsorship" ? "Event Deal" : "Creator Deal"}</span>
                    <h3>{deal.deal_type === "sponsorship" ? deal.event?.title || "Event partnership" : deal.campaign?.title || "Creator campaign"}</h3>
                    <p>{role === "sponsor" ? (deal.deal_type === "sponsorship" ? deal.organizerName : deal.influencerName) : deal.sponsorName}</p>
                    <div className="activity-center-meta-row">
                      <span>#{deal.id}</span>
                      <span>{(deal.status || "pending").replace("_", " ")}</span>
                      <span>{formatCurrency(Number(deal.paymentAmount) || 0)}</span>
                    </div>
                  </button>
                </DealCard>
              ))}

              {section === "events" && filteredItems.map((event) => (
                <div key={event.id} className="activity-center-card">
                  <span className="activity-center-chip">{event.category || "Event"}</span>
                  <h3>{event.title}</h3>
                  <p>{event.city || "Location TBD"}</p>
                  <div className="activity-center-meta-row">
                    <span>#{event.id}</span>
                    <span>{formatCurrency(event.budget)}</span>
                  </div>
                </div>
              ))}

              {section === "discovery" && filteredItems.map((item) => (
                <div key={item.id} className="activity-center-card">
                  <span className="activity-center-chip">{role === "organizer" ? "Sponsor" : "Creator"}</span>
                  <h3>{item.name}</h3>
                  <p>{role === "organizer" ? `${item.focus} | ${item.city}` : `${item.niche} | ${item.platforms}`}</p>
                  <div className="activity-center-meta-row">
                    <span>#{item.id}</span>
                    {role !== "organizer" && <span>Audience {Number(item.audience || 0).toLocaleString("en-IN")}</span>}
                  </div>
                </div>
              ))}

              {section === "opportunities" && filteredItems.map((campaign) => (
                <div key={campaign.id} className="activity-center-card">
                  <span className="activity-center-chip">{campaign.platform_required || "Campaign"}</span>
                  <h3>{campaign.title}</h3>
                  <p>{campaign.description}</p>
                  <div className="activity-center-meta-row">
                    <span>#{campaign.id}</span>
                    <span>{formatCurrency(Number(campaign.budget) || 0)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {selectedDeal && (
        <ActivityProgressModal
          deal={selectedDeal}
          role={role}
          isReviewed={Boolean(reviewedDeals[selectedDeal.id])}
          onClose={() => setSelectedDeal(null)}
          onOpenDetails={selectedDeal.deal_type === "sponsorship" ? () => openDealEventDetails(selectedDeal) : null}
          actions={{
            accept: (
              (role === "sponsor" && !selectedDeal.sponsorAccepted) ||
              (role === "organizer" && !selectedDeal.organizerAccepted) ||
              (role === "influencer" && !selectedDeal.influencerAccepted)
            )
              ? () => handleDealAction(selectedDeal.id, acceptDeal, { role, accept: true }, "Deal accepted.")
              : null,
            pay:
              role === "sponsor" && selectedDeal.status === "payment_pending" && !selectedDeal.paymentDone
                ? () => handleStartPayment(selectedDeal)
                : null,
            sign: (
              selectedDeal.paymentDone && (
                (role === "sponsor" && !selectedDeal.sponsorSigned) ||
                (role === "organizer" && !selectedDeal.organizerSigned) ||
                (role === "influencer" && !selectedDeal.influencerSigned)
              )
            )
              ? () => handleStartSigning(selectedDeal)
              : null,
            review:
              selectedDeal.status === "closed" && !reviewedDeals[selectedDeal.id]
                ? () => {
                    setReviewDeal(selectedDeal);
                    setShowReviewModal(true);
                  }
                : null,
            chat: () => setActiveDealChat(selectedDeal),
            agreement: (
              (role === "sponsor" && selectedDeal.sponsorSigned) ||
              (role === "organizer" && selectedDeal.organizerSigned) ||
              (role === "influencer" && selectedDeal.influencerSigned)
            )
              ? () => setShowDocument({ type: "agreement", deal: selectedDeal })
              : null,
            invoice: selectedDeal.paymentDone ? () => setShowDocument({ type: "invoice", deal: selectedDeal }) : null,
          }}
          formatCurrency={formatCurrency}
        />
      )}

      {showPaymentModal && paymentDeal && (
        <PaymentModal
          amount={paymentDeal.paymentAmount}
          currency={paymentDeal.currency}
          onSuccess={handlePaymentSuccess}
          onClose={() => setShowPaymentModal(false)}
        />
      )}

      {showAgreementModal && signDeal && (
        <AgreementModal
          deal={signDeal}
          role={role}
          onSign={handleSignSuccess}
          onClose={() => {
            setShowAgreementModal(false);
            setSignDeal(null);
          }}
        />
      )}

      {showReviewModal && reviewDeal && (
        <ReviewModal
          deal={reviewDeal}
          reviewerRole={role}
          targetRole={getReviewTargetRole(role, reviewDeal.deal_type)}
          onSubmit={handleReviewSubmit}
          onClose={() => {
            setShowReviewModal(false);
            setReviewDeal(null);
          }}
        />
      )}

      {activeDealChat && (
        <ChatBox
          role={role}
          title={`Chat: ${getChatPartnerName(activeDealChat, role)}`}
          chatKey={`deal_${activeDealChat.id}`}
          onClose={() => setActiveDealChat(null)}
        />
      )}

      {showDocument && (
        <DocumentViewer
          type={showDocument.type}
          deal={showDocument.deal}
          onClose={() => setShowDocument(null)}
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

export default ActivityCenterPage;
