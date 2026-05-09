const DEVICE_KEY = "client_device_id";
let memoryDeviceId = "";

function createDeviceId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `device-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getOrCreateDeviceId() {
  try {
    const existing = localStorage.getItem(DEVICE_KEY);
    if (existing) {
      return existing;
    }

    const next = createDeviceId();
    localStorage.setItem(DEVICE_KEY, next);
    return next;
  } catch (_error) {
    if (memoryDeviceId) {
      return memoryDeviceId;
    }
    memoryDeviceId = createDeviceId();
    return memoryDeviceId;
  }
}
