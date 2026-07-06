import { computed, ref } from "vue";

const STORAGE_KEY = "aid_helper_saved_request_ids";

function readSavedIds() {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return Array.isArray(value) ? value.map(Number).filter(Number.isFinite) : [];
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return [];
  }
}

const ids = ref(readSavedIds());

function persist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids.value));
}

export function isRequestSaved(requestId) {
  return ids.value.includes(Number(requestId));
}

export function toggleSavedRequest(requestId) {
  const id = Number(requestId);
  ids.value = isRequestSaved(id) ? ids.value.filter((item) => item !== id) : [...ids.value, id];
  persist();
}

export function removeSavedRequest(requestId) {
  ids.value = ids.value.filter((item) => item !== Number(requestId));
  persist();
}

export const savedRequestIds = computed(() => ids.value);
