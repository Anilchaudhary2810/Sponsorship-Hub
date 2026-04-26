import axios from "axios";
import toast from "react-hot-toast";

// Cookie-only auth strategy. Keep these exports for backward compatibility,
// but never store bearer tokens in browser storage.
export const setAccessToken = () => {};
export const getAccessToken = () => null;
export const clearAccessToken = () => {};

const normalizeLocalApiBase = (rawBaseUrl) => {
  if (typeof window === "undefined") {
    return rawBaseUrl || "http://localhost:8000";
  }

  const pageHost = window.location.hostname;
  const fallback = `http://${pageHost}:8000`;
  const baseCandidate = rawBaseUrl || fallback;

  try {
    const parsed = new URL(baseCandidate, window.location.origin);
    const isLoopback = (host) =>
      host === "localhost" || host === "127.0.0.1" || host === "::1";

    // In local dev, force API host to match current page host so
    // SameSite=Lax cookies remain first-party and are sent on XHR/WS.
    if (isLoopback(parsed.hostname) && isLoopback(pageHost) && parsed.hostname !== pageHost) {
      parsed.hostname = pageHost;
    }

    return parsed.toString().replace(/\/$/, "");
  } catch {
    return fallback;
  }
};

export const API_BASE_URL = normalizeLocalApiBase(import.meta.env.VITE_API_URL);
export const WS_BASE_URL = API_BASE_URL.replace(/^http/i, "ws");

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

let refreshPromise = null;

const PUBLIC_AUTH_PATHS = new Set([
  "/login",
  "/register",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
]);

const isOnPublicAuthPage = () => {
  if (typeof window === "undefined") return false;
  const path = window.location.pathname || "";
  return PUBLIC_AUTH_PATHS.has(path);
};

const shouldSkipRefresh = (url = "") =>
  url.includes("/auth/login") ||
  url.includes("/auth/register") ||
  url.includes("/auth/verify-email") ||
  url.includes("/auth/resend-verification") ||
  url.includes("/auth/request-password-reset") ||
  url.includes("/auth/reset-password") ||
  url.includes("/auth/refresh") ||
  url.includes("/auth/logout");

const handleAuthFailure = (message) => {
  localStorage.removeItem("currentUser");

  // Do not interrupt public auth flows (login/register/verify/reset) with
  // "Session expired" UX noise.
  if (isOnPublicAuthPage()) {
    return;
  }

  if (message) {
    toast.error(`Session expired: ${message}`);
  } else {
    toast.error("Session expired. Please log in again.");
  }

  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
};

const getCookieValue = (name) => {
  const cookieString = document.cookie || "";
  const parts = cookieString.split(";").map((v) => v.trim());
  const found = parts.find((p) => p.startsWith(`${name}=`));
  if (!found) return null;
  return decodeURIComponent(found.substring(name.length + 1));
};

api.interceptors.request.use((config) => {
  const method = String(config.method || "get").toUpperCase();
  const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);
  if (unsafeMethods.has(method)) {
    const csrfToken = getCookieValue("csrf_token");
    if (csrfToken) {
      config.headers["X-CSRF-Token"] = csrfToken;
    }
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const isUnauthorized = error.response?.status === 401;
    const requestUrl = originalRequest.url || "";
    const skipRefresh = shouldSkipRefresh(requestUrl);

    if (!isUnauthorized || originalRequest._retry || skipRefresh) {
      if (isUnauthorized && !skipRefresh) {
        const errorMessage = error.response?.data?.message || error.response?.data?.detail;
        handleAuthFailure(errorMessage);
      }
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = api.post("/auth/refresh", { refresh_token: null });
      }

      const refreshResponse = await refreshPromise;
      const refreshedUser = refreshResponse?.data?.user;

      if (refreshedUser) {
        localStorage.setItem("currentUser", JSON.stringify(refreshedUser));
      }

      return api(originalRequest);
    } catch (refreshError) {
      const errorMessage =
        refreshError?.response?.data?.message ||
        refreshError?.response?.data?.detail ||
        "Authentication failed";
      handleAuthFailure(errorMessage);
      return Promise.reject(refreshError);
    } finally {
      refreshPromise = null;
    }
  }
);

export default api;
