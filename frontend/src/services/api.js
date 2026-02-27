import axios from "axios";
import toast from "react-hot-toast";

// create axios instance with base URL and interceptors
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
});

// attach token from localStorage on each request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("authToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// global error handler
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Backend custom error shape: { error, message, code }
    // FastAPI default shape:      { detail: string | list }
    let message =
      error.response?.data?.message ||   // custom backend shape (primary)
      error.response?.data?.detail ||    // FastAPI default shape
      error.message;                     // network/axios error

    // Handle FastAPI 422 validation errors — detail is a list of objects
    if (typeof message === "object" && message !== null) {
      if (Array.isArray(message)) {
        const err = message[0];
        const field = err?.loc ? err.loc[err.loc.length - 1] : "Unknown field";
        message = `Error in '${field}': ${err?.msg || "Invalid value"}`;
      } else {
        message = JSON.stringify(message);
      }
    }

    if (message) toast.error(message);

    // Auto-logout on 401 Unauthorized (expired/invalid token)
    if (error.response?.status === 401) {
      localStorage.removeItem("authToken");
      localStorage.removeItem("currentUser");
      if (!window.location.pathname.includes("/login")) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

// --- auth & user endpoints ---
export const registerUser = (payload) => api.post("/auth/register", payload);
export const loginUser = (payload) => api.post("/auth/login", payload);
export const fetchUser = (id) => api.get(`/users/${id}/`);
export const updateUser = (id, updates) => api.put(`/users/${id}/`, updates);
export const forgotPassword = (data) => api.post("/auth/request-password-reset", data);
export const resetPassword = (data) => api.post("/auth/reset-password", data);
export const fetchUserProfile = (id) => api.get(`/users/${id}/profile`);
export const getUsersByRole = (role) => api.get(`/users/?role=${role}`);

// --- events ---
export const fetchEvents = () => api.get("/events/");
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
export const fetchCampaigns = () => api.get("/campaigns/");
export const createCampaign = (data) => api.post("/campaigns/", data);
export const updateCampaign = (id, data) => api.put(`/campaigns/${id}`, data);

// --- reviews ---
export const createReview = (data) => api.post("/reviews/", data);
export const fetchReviews = () => api.get("/reviews/");
export const fetchReviewsForDeal = (dealId) => api.get(`/reviews/${dealId}`);
export const fetchMyReviews = () => api.get("/reviews/my"); // { "dealId": rating }

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
