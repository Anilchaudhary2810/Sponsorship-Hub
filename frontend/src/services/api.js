import api from "../api/api";

// --- auth & user endpoints ---
export const registerUser = (payload) => api.post("/auth/register", payload);
export const loginUser = (payload) => api.post("/auth/login", payload);
export const logoutUser = () => api.post("/auth/logout");
export const fetchUser = (id) => api.get(`/users/${id}/`);
export const updateUser = (id, updates) => api.put(`/users/${id}/`, updates);
export const forgotPassword = (data) => api.post("/auth/request-password-reset", data);
export const resetPassword = (data) => api.post("/auth/reset-password", data);
export const verifyEmailToken = (token) => api.get("/auth/verify-email", { params: { token } });
export const resendVerificationEmail = (data) => api.post("/auth/resend-verification", data);
export const fetchUserProfile = (id) => api.get(`/users/${id}/profile`);
export const getUsersByRole = (role) => api.get(`/users/?role=${role}`);
export const fetchPublicStats = () => api.get("/stats/public");
export const fetchMarketplaceSnapshot = (params = {}) => api.get("/stats/marketplace-snapshot", { params });
export const fetchBillingPlans = () => api.get("/billing/plans");
export const fetchMyBilling = () => api.get("/billing/me");
export const changeMyPlan = (data) => api.post("/billing/me/change-plan", data);
export const fetchMyBillingHistory = () => api.get("/billing/me/history");
export const fetchTrustProfile = () => api.get("/trust/me");
export const submitKyc = (data) => api.post("/trust/kyc/submit", data);
export const fetchPendingKycSubmissions = () => api.get("/trust/kyc/pending");
export const reviewKycSubmission = (submissionId, data) => api.put(`/trust/kyc/${submissionId}/review`, data);

// --- admin ops ---
export const fetchOpsMetrics = () => api.get("/ops/metrics");
export const fetchOpsAuditEvents = (params = {}) => api.get("/ops/audit-events", { params });
export const fetchOpsPlanDistribution = () => api.get("/ops/plan-distribution");

// --- proposal quality tools ---
export const fetchDealTemplates = (dealType) =>
  api.get("/proposal/templates", { params: dealType ? { deal_type: dealType } : {} });
export const createDealTemplate = (data) => api.post("/proposal/templates", data);
export const updateDealTemplate = (templateId, data) => api.put(`/proposal/templates/${templateId}`, data);
export const deleteDealTemplate = (templateId) => api.delete(`/proposal/templates/${templateId}`);
export const fetchDealApprovals = (dealId) => api.get(`/proposal/deals/${dealId}/approvals`);
export const requestDealApproval = (dealId, data) => api.post(`/proposal/deals/${dealId}/approvals`, data);
export const decideDealApproval = (approvalId, data) => api.put(`/proposal/approvals/${approvalId}/decision`, data);
export const fetchNegotiations = (dealId) => api.get(`/proposal/deals/${dealId}/negotiations`);
export const createNegotiationEntry = (dealId, data) => api.post(`/proposal/deals/${dealId}/negotiations`, data);

// --- revenue confidence ---
export const fetchDealMilestones = (dealId) => api.get(`/revenue/deals/${dealId}/milestones`);
export const createDealMilestone = (dealId, data) => api.post(`/revenue/deals/${dealId}/milestones`, data);
export const updateMilestoneAction = (milestoneId, action) => api.put(`/revenue/milestones/${milestoneId}/action`, { action });
export const fetchEscrowState = (dealId) => api.get(`/revenue/deals/${dealId}/escrow`);
export const fetchDealDisputes = (dealId) => api.get(`/revenue/deals/${dealId}/disputes`);
export const openDealDispute = (dealId, data) => api.post(`/revenue/deals/${dealId}/disputes`, data);
export const resolveDealDispute = (disputeId, data) => api.put(`/revenue/disputes/${disputeId}/resolve`, data);
export const fetchPayoutSummary = (dealId) => api.get(`/revenue/deals/${dealId}/payout-summary`);

// --- collaboration ---
export const createWorkspace = (data) => api.post("/collaboration/workspaces", data);
export const fetchWorkspaces = () => api.get("/collaboration/workspaces");
export const fetchWorkspace = (workspaceId) => api.get(`/collaboration/workspaces/${workspaceId}`);
export const inviteWorkspaceMember = (workspaceId, data) => api.post(`/collaboration/workspaces/${workspaceId}/members`, data);
export const updateWorkspaceMember = (workspaceId, memberId, data) =>
  api.put(`/collaboration/workspaces/${workspaceId}/members/${memberId}`, data);
export const removeWorkspaceMember = (workspaceId, memberId) =>
  api.delete(`/collaboration/workspaces/${workspaceId}/members/${memberId}`);
export const fetchWorkspaceResources = (workspaceId) => api.get(`/collaboration/workspaces/${workspaceId}/resources`);
export const addWorkspaceResource = (workspaceId, data) =>
  api.post(`/collaboration/workspaces/${workspaceId}/resources`, data);
export const removeWorkspaceResource = (workspaceId, resourceRowId) =>
  api.delete(`/collaboration/workspaces/${workspaceId}/resources/${resourceRowId}`);

// --- retention ---
export const generateMyNudges = () => api.post("/retention/generate");
export const fetchMyNudges = (state) => api.get("/retention/me", { params: state ? { state } : {} });
export const updateNudgeState = (nudgeId, state) => api.put(`/retention/${nudgeId}`, { state });

// --- reporting ---
export const fetchROIReport = (days = 30) => api.get("/reports/roi", { params: { days } });
export const fetchCampaignOutcomes = () => api.get("/reports/campaign-outcomes");
export const fetchMonthlyExecutiveReport = (month) =>
  api.get("/reports/monthly-executive", { params: month ? { month } : {} });
export const fetchReportSnapshots = (reportType) =>
  api.get("/reports/snapshots", { params: reportType ? { report_type: reportType } : {} });
export const exportCampaignOutcomesCsvUrl = () =>
  `${api.defaults.baseURL || ""}/reports/campaign-outcomes/export.csv`;

// --- integrations ---
export const fetchIntegrations = () => api.get("/integrations/connections");
export const connectIntegration = (provider, config_json = {}) => api.post("/integrations/connect", { provider, config_json });
export const disconnectIntegration = (provider) => api.delete(`/integrations/${provider}`);
export const syncIntegration = (provider, event_type, payload = {}) =>
  api.post(`/integrations/${provider}/sync`, { event_type, payload });
export const fetchIntegrationEvents = (provider) => api.get(`/integrations/${provider}/events`);
export const sendIntegrationTestAlert = (provider, payload = {}) =>
  api.post(`/integrations/${provider}/test-alert`, { event_type: `${provider}_test`, payload });
export const exportSheetsCsvUrl = () => `${api.defaults.baseURL || ""}/integrations/sheets/export.csv`;
export const exportCalendarIcsUrl = () => `${api.defaults.baseURL || ""}/integrations/calendar/export.ics`;

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
export const createPaymentOrder = (id, options = {}) =>
  api.post(`/payments/create-order?deal_id=${id}${options?.forceNew ? "&force_new=true" : ""}`);
export const fetchPaymentCheckoutConfig = () => api.get("/payments/checkout-config");
export const verifyPayment = (data) => api.post("/payments/verify", data);
// Backward-compatible alias: now creates payment order instead of manual payment marking.
export const markPaymentDone = (id, _payment) => createPaymentOrder(id);
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

// --- AI assistant ---
export const fetchAIContext = (params = {}) => api.get("/ai-assistant/context", { params });
export const fetchPublicAIContext = (params = {}) => api.get("/ai-assistant/public-context", { params });
export const fetchAIHistory = (limit = 80) => api.get("/ai-assistant/history", { params: { limit } });
export const clearAIHistory = () => api.delete("/ai-assistant/history");
export const sendAIMessage = (data) => api.post("/ai-assistant/message", data);
export const sendPublicAIMessage = (data) => api.post("/ai-assistant/public-message", data);

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
