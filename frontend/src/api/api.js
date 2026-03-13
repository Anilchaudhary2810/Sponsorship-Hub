import axios from "axios";
import toast from "react-hot-toast";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("currentUser");
      
      const errorMessage = error.response?.data?.message || error.response?.data?.detail;
      if (errorMessage) {
        toast.error(`Session expired: ${errorMessage}`);
      } else {
        toast.error("Session expired. Please log in again.");
      }
    }
    return Promise.reject(error);
  }
);

export default api;
