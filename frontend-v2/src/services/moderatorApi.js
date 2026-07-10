import api from "./api";

function page(data) {
  if (Array.isArray(data)) return { count: data.length, next: null, previous: null, results: data };
  return {
    count: data?.count || 0,
    next: data?.next || null,
    previous: data?.previous || null,
    results: Array.isArray(data?.results) ? data.results : [],
  };
}

export async function getModerationQueue(params = {}) {
  const { data } = await api.get("/requests/moderation/queue/", { params });
  return page(data);
}

export async function getModerationRequests(params = {}) {
  const { data } = await api.get("/moderation/requests/", { params });
  return page(data);
}

export async function decideModerationRequest(requestId, action, comment = "") {
  const { data } = await api.post(`/requests/moderation/${requestId}/`, { action, comment });
  return data;
}

export async function getFraudDecision(requestId) {
  const { data } = await api.get(`/fraud/requests/${requestId}/decision/`);
  return data;
}

export async function getFraudChecks(requestId) {
  const { data } = await api.get(`/fraud/requests/${requestId}/checks/`);
  return page(data);
}

export async function recheckFraud(requestId) {
  const { data } = await api.post(`/fraud/requests/${requestId}/recheck/`);
  return data;
}

export async function overrideFraud(requestId, newAction, comment) {
  const { data } = await api.post(`/fraud/requests/${requestId}/override/`, {
    new_action: newAction,
    comment,
  });
  return data;
}

export async function getVerificationQueue(params = {}) {
  const { data } = await api.get("/moderation/verifications/", { params });
  return page(data);
}

export async function decideVerification(verificationId, decision, comment = "") {
  const { data } = await api.post(`/moderation/verifications/${verificationId}/decision/`, { decision, comment });
  return data;
}

export async function getModeratorFulfillment(requestId) {
  const { data } = await api.get(`/moderation/requests/${requestId}/fulfillment/`);
  return data;
}

export async function getRequestHistory(requestId) {
  const { data } = await api.get(`/requests/${requestId}/history/`);
  return Array.isArray(data) ? data : [];
}

export function getModeratorApiError(error, fallback = "Не удалось выполнить операцию") {
  const data = error?.response?.data;
  const code = data?.code;
  if (code === "fraud_publication_blocked") {
    return "Публикация запрещена антифрод-политикой. Выполните override или отклоните заявку.";
  }
  if (code === "fraud_decision_missing") {
    return "Антифрод-решение отсутствует. Выполните повторную проверку или отклоните заявку.";
  }
  if (typeof data === "string") return data;
  if (data?.detail) return data.detail;
  if (data && typeof data === "object") {
    const message = Object.values(data).flat().find((value) => typeof value === "string");
    if (message) return message;
  }
  const messages = {
    400: "Проверьте введённые данные или текущее состояние заявки.",
    401: "Сессия завершена. Войдите снова.",
    403: "У вашей роли нет доступа к этой операции.",
    404: "Заявка или служебные данные не найдены.",
    409: "Операция конфликтует с текущим состоянием заявки.",
  };
  return messages[error?.response?.status] || (error?.response ? fallback : "Сервер недоступен. Попробуйте снова позже.");
}
