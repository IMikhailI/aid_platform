import { computed, reactive, readonly } from "vue";
import api from "../services/api";
import {
  clearAuth,
  getAccessToken,
  getStoredUser,
  setStoredUser,
  setTokens,
} from "../services/auth";

const state = reactive({
  user: getStoredUser(),
  accessToken: getAccessToken(),
  loading: false,
  initialized: false,
});

export const currentUser = computed(() => state.user);
export const currentRole = computed(() => state.user?.role || "");
export const isAuthenticated = computed(() => Boolean(state.accessToken));

export function redirectByRole(role = currentRole.value) {
  if (role === "applicant") return "/applicant";
  if (role === "helper") return "/helper";
  if (role === "moderator" || role === "admin") return "/moderator";
  return "/login";
}

export async function fetchMe() {
  try {
    const { data } = await api.get("/auth/me/");
    state.user = data;
    state.accessToken = getAccessToken();
    setStoredUser(data);
    return data;
  } finally {
    state.initialized = true;
  }
}

export async function login(username, password) {
  state.loading = true;
  try {
    const { data } = await api.post("/auth/token/", { username, password });
    setTokens(data);
    state.accessToken = data.access || getAccessToken();
    return await fetchMe();
  } catch (error) {
    logout();
    throw error;
  } finally {
    state.loading = false;
  }
}

export async function register(payload) {
  state.loading = true;
  try {
    const { data } = await api.post("/auth/register/", payload);
    return data;
  } finally {
    state.loading = false;
  }
}

export function logout() {
  clearAuth();
  state.user = null;
  state.accessToken = "";
  state.initialized = true;
}

window.addEventListener("auth:logout", logout);

export const authStore = {
  state: readonly(state),
  currentUser,
  currentRole,
  isAuthenticated,
  login,
  register,
  logout,
  fetchMe,
  redirectByRole,
};
