import api from "./api";

function asList(data) {
  if (Array.isArray(data)) return data;
  return Array.isArray(data?.results) ? data.results : [];
}

export async function getApplicantProfile() {
  const { data } = await api.get("/applicant/profile/");
  return data;
}

export async function updateApplicantProfile(payload) {
  const { data } = await api.patch("/applicant/profile/", payload);
  return data;
}

export async function submitApplicantVerification() {
  const { data } = await api.post("/applicant/verification/submit/");
  return data;
}

export async function getApplicantVerificationHistory() {
  const { data } = await api.get("/applicant/verification/history/");
  return asList(data);
}

export async function getApplicantRequests() {
  const { data } = await api.get("/requests/applicant/my/");
  return asList(data);
}

export async function createApplicantRequest(payload) {
  const { data } = await api.post("/requests/applicant/create/", payload);
  return data;
}

export async function getApplicantFulfillment(requestId) {
  const { data } = await api.get(`/applicant/requests/${requestId}/fulfillment/`);
  return data;
}

export async function confirmApplicantReceipt(requestId) {
  const { data } = await api.post(`/applicant/requests/${requestId}/confirm-receipt/`);
  return data;
}

export function getApplicantApiError(error, fallback = "Не удалось выполнить запрос") {
  if (!error?.response) return "Сервер недоступен. Проверьте подключение и попробуйте снова";
  if (error.response.status === 401) return "Сессия завершена. Войдите снова";
  if (error.response.status === 403) return "Недостаточно прав для выполнения этого действия";
  if (error.response.status === 404) return "Данные пока недоступны";

  const data = error.response.data;
  if (typeof data === "string") return data;
  if (data?.detail) return data.detail;

  if (data && typeof data === "object") {
    const message = Object.values(data).flat().find((value) => typeof value === "string");
    if (message) return message;
  }
  if (error.response.status === 409) return "Действие уже выполнено или недоступно в текущем состоянии";
  if (error.response.status === 400) return "Проверьте заполненные данные";
  return fallback;
}
