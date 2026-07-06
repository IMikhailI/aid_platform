import axios from "axios";
import { clearAuth, getAccessToken, getRefreshToken, setTokens } from "./auth";

const baseURL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api").replace(/\/$/, "");

const api = axios.create({ baseURL, timeout: 15000 });
const refreshClient = axios.create({ baseURL, timeout: 15000 });
let refreshPromise = null;

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config;
    const refresh = getRefreshToken();
    const isAuthRequest = request?.url?.includes("/auth/token/");

    if (error.response?.status !== 401 || request?._retry || !refresh || isAuthRequest) {
      return Promise.reject(error);
    }

    request._retry = true;
    refreshPromise ??= refreshClient
      .post("/auth/token/refresh/", { refresh })
      .then(({ data }) => {
        setTokens({ access: data.access, refresh });
        return data.access;
      })
      .catch((refreshError) => {
        clearAuth();
        window.dispatchEvent(new Event("auth:logout"));
        throw refreshError;
      })
      .finally(() => {
        refreshPromise = null;
      });

    const access = await refreshPromise;
    request.headers.Authorization = `Bearer ${access}`;
    return api(request);
  },
);

export default api;
