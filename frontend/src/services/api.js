import axios from "axios";
import { clearAuth, getAccessToken, getRefreshToken, setAuth, getRole, getUsername } from "./auth";
import { getOrCreateDeviceId } from "./device";

const api = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 15000,
});

// Подставляем access token в каждый запрос
api.interceptors.request.use((config) => {
  const token = getAccessToken();
  config.headers = config.headers || {};
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  config.headers["X-Device-Id"] = getOrCreateDeviceId();
  return config;
});

// Авто-refresh токена при 401
let isRefreshing = false;
let queue = [];

function processQueue(error, token = null) {
  queue.forEach((p) => {
    if (error) p.reject(error);
    else p.resolve(token);
  });
  queue = [];
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;

    if (
      error.response &&
      error.response.status === 401 &&
      !originalRequest._retry &&
      getRefreshToken()
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refresh = getRefreshToken();
        const resp = await axios.post("http://localhost:8000/api/auth/token/refresh/", { refresh });
        const newAccess = resp.data.access;

        setAuth({
          access: newAccess,
          refresh,
          role: getRole(),
          username: getUsername(),
        });

        processQueue(null, newAccess);
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return api(originalRequest);
      } catch (e) {
        processQueue(e, null);
        clearAuth();
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;
