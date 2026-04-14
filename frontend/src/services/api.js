import api from "../api/api";

// --- auth & user endpoints ---
export const registerUser = (payload) => api.post("/auth/register", payload);
export const loginUser = (payload) => api.post("/auth/login", payload);
export const logoutUser = () => api.post("/auth/logout");
export const fetchUser = (id) => api.get(`/users/${id}/`);
export const updateUser = (id, updates) => api.put(`/users/${id}/`, updates);
export const forgotPassword = (data) => api.post("/auth/request-password-reset", data);
export const resetPassword = (data) => api.post("/auth/reset-password", data);
export const fetchUserProfile = (id) => api.get(`/users/${id}/profile`);
export const getUsersByRole = (role) => api.get(`/users/?role=${role}`);
export const fetchPublicStats = () => api.get("/stats/public");
export const fetchMarketplaceSnapshot = (params = {}) => api.get("/stats/marketplace-snapshot", { params });
export const fetchBillingPlans = () => api.get("/billing/plans");
export const fetchMyBilling = () => api.get("/billing/me");
export const changeMyPlan = (data) => api.post("/billing/me/change-plan", data);
export const fetchMyBillingHistory = () => api.get("/billing/me/history");

// --- events ---
export const fetchEvents = (params = {}) => api.get("/events/", { params });
export const createEvent = (data) => api.post("/events/", data);
export const updateEvent = (id, data) => api.put(`/events/${id}`, data);
export const deleteEvent = (id) => api.delete(`/events/${id}`);

// --- deals ---
export const fetchDeals = () => api.get("/deals/");
export const fetchDeal = (id) => api.get(`/deals/${id}`);
export const createDeal = (data) => api.post("/deals/", data);
export const updateDeal = (id, data) => api.put(`/deals/${id}`, data);
export const deleteDeal = (id) => api.delete(`/deals/${id}`);
export const acceptDeal = (id, action) => api.put(`/deals/${id}/accept`, action);
export const markPaymentDone = (id, payment) => api.put(`/deals/${id}/payment`, payment);
export const signDeal = (id, sign) => api.put(`/deals/${id}/sign`, sign);

// --- campaigns ---
export const fetchCampaigns = (params = {}) => api.get("/campaigns/", { params });
export const createCampaign = (data) => api.post("/campaigns/", data);
export const updateCampaign = (id, data) => api.put(`/campaigns/${id}`, data);

// --- reviews ---
export const createReview = (data) => api.post("/reviews/", data);
export const fetchReviews = () => api.get("/reviews/");
export const fetchReviewsForDeal = (dealId) => api.get(`/reviews/${dealId}`);
export const fetchMyReviews = () => api.get("/reviews/my"); // { "dealId": rating }
export const fetchChatHistory = (dealId) => api.get(`/chat/history/${dealId}`);

// --- notifications ---
export const fetchNotifications = () => api.get("/notifications/");
export const markNotificationRead = (id) => api.put(`/notifications/${id}/read`);
export const markAllNotificationsRead = () => api.put("/notifications/read-all");

// helpers for UI
export const getAvailableSponsors = () => fetchUsersByRole("sponsor");
export const getAvailableOrganizers = () => fetchUsersByRole("organizer");
export const getAvailableInfluencers = () => fetchUsersByRole("influencer");

// internal helper
const fetchUsersByRole = async (role) => {
  // Use backend role filter to avoid "list all" admin restriction
  const resp = await api.get(`/users/?role=${role}`);
  return resp.data;
};
