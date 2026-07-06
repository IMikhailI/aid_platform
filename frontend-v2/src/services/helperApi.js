import api from "./api";

export async function getPublishedRequests(params = {}) {
  const { data } = await api.get("/requests/published/", { params });
  return Array.isArray(data) ? data : data.results || [];
}

export async function takeRequest(requestId, payload = {}) {
  const { data } = await api.post(`/requests/helper/take/${requestId}/`, {
    method: payload.method || "certificate",
    note: payload.note || "",
  });
  return data;
}

export async function getFulfillment(requestId) {
  const { data } = await api.get(`/helper/requests/${requestId}/fulfillment/`);
  return data;
}

export async function createFulfillment(requestId, payload) {
  const { data } = await api.post(`/helper/requests/${requestId}/fulfillment/`, {
    provider_name: payload.provider_name,
    amount: payload.amount,
  });
  return data;
}

export async function deliverFulfillment(requestId) {
  const { data } = await api.post(`/helper/requests/${requestId}/fulfillment/deliver/`);
  return data;
}

export function getHelperApiError(error, fallback = "Не удалось выполнить операцию.") {
  const messages = {
    401: "Сессия завершена. Войдите снова.",
    403: "У вашей роли нет доступа к этой операции.",
    404: "Заявка не найдена или больше недоступна.",
    409: "Операция недоступна: состояние заявки уже изменилось.",
  };

  return error.response?.data?.detail || messages[error.response?.status] || fallback;
}
