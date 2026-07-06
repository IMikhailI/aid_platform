const ACCESS_KEY = "aid_access_token";
const REFRESH_KEY = "aid_refresh_token";
const USER_KEY = "aid_current_user";

export const getAccessToken = () => localStorage.getItem(ACCESS_KEY) || "";
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY) || "";

export function setTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
}

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY)) || null;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function setStoredUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}
