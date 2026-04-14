import axios from "axios";
import toast from "react-hot-toast";

const ACCESS_TOKEN_KEY = "access_token";

const readStoredToken = () => {
  try {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
};

const writeStoredToken = (token) => {
  try {
    if (token) {
      sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
    } else {
      sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    }
  } catch {
    // Ignore storage failures (private mode, blocked storage, etc.)
  }
};

let accessToken = readStoredToken();

export const setAccessToken = (token) => {
  accessToken = token || null;
  writeStoredToken(accessToken);
};

export const getAccessToken = () => accessToken;

export const clearAccessToken = () => {
  accessToken = null;
  writeStoredToken(null);
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  withCredentials: true,
});

let refreshPromise = null;

const shouldSkipRefresh = (url = "") =>
  url.includes("/auth/login") ||
  url.includes("/auth/register") ||
  url.includes("/auth/refresh") ||
  url.includes("/auth/logout");

const handleAuthFailure = (message) => {
  clearAccessToken();
  localStorage.removeItem("currentUser");

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
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

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

    if (!isUnauthorized || originalRequest._retry || shouldSkipRefresh(originalRequest.url || "")) {
      if (isUnauthorized) {
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
      const refreshedToken = refreshResponse?.data?.access_token;
      const refreshedUser = refreshResponse?.data?.user;

      if (!refreshedToken) {
        throw new Error("Missing refreshed access token");
      }

      setAccessToken(refreshedToken);
      if (refreshedUser) {
        localStorage.setItem("currentUser", JSON.stringify(refreshedUser));
      }

      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${refreshedToken}`;
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
