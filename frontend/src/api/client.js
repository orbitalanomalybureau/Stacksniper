import axios from "axios";

const apiClient = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "http://localhost:8000",
  withCredentials: true, // Send httpOnly cookies for refresh token
  headers: {
    "Content-Type": "application/json",
  },
});

// In-memory token storage (NOT localStorage — prevents XSS)
let accessToken = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function clearAccessToken() {
  accessToken = null;
}

// Attach access token to every request
apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// Handle 401 — attempt token refresh (only for authenticated requests)
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    // Only attempt refresh if the original request had an auth header
    // and it's not already a retry or a refresh/login request
    const isAuthRequest = originalRequest.headers?.Authorization;
    const isAuthEndpoint = originalRequest.url?.includes("/api/auth/");
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      isAuthRequest &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;
      try {
        const { data } = await apiClient.post("/api/auth/refresh");
        setAccessToken(data.access_token);
        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(originalRequest);
      } catch {
        clearAccessToken();
      }
    }
    // Dispatch error event for non-401 errors (401 is handled above)
    const status = error.response?.status;
    if (status && status !== 401) {
      const message = error.response?.data?.detail || error.message;
      window.dispatchEvent(new CustomEvent("api-error", { detail: { status, message } }));
    }
    return Promise.reject(error);
  }
);

export default apiClient;
