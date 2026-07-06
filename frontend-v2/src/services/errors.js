export function getApiError(error, fallback) {
  const data = error.response?.data;

  if (typeof data === "string" && data.trim()) return data;
  if (data?.detail) return data.detail;

  if (data && typeof data === "object") {
    const firstError = Object.values(data).flat().find((value) => typeof value === "string");
    if (firstError) return firstError;
  }

  return fallback;
}
