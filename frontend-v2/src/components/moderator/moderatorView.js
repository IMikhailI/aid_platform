export const categories = {
  food: "Еда",
  children: "Детские товары",
  medicine: "Лекарства",
  clothes: "Одежда",
  other: "Другое",
};

export const categoryIcons = {
  food: "store.svg",
  children: "baby-face.svg",
  medicine: "pill.svg",
  clothes: "shirt.svg",
  other: "package-box.svg",
};

export const verificationLabels = {
  not_submitted: "Не отправлен",
  pending: "На проверке",
  verified: "Проверен",
  rejected: "Отклонён",
};

export const fraudActions = {
  allow: "Разрешить",
  manual_review: "Ручная проверка",
  block: "Блокировать",
};

export function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "Не указана";
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(Number(value))} ₽`;
}

export function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
}

export function riskLevel(request, decision = null) {
  if (decision?.risk_level) return decision.risk_level;
  const score = Number(request?.risk_score || 0);
  if (request?.is_flagged || score >= 70) return "high";
  if (score >= 40) return "medium";
  return "low";
}
