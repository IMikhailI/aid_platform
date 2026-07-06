export const requestStatus = {
  draft: ["Черновик", "neutral"],
  on_moderation: ["На модерации", "warning"],
  published: ["Опубликована", "info"],
  in_progress: ["В работе", "violet"],
  closed: ["Завершена", "success"],
  rejected: ["Отклонена", "danger"],
};

export const verificationStatus = {
  not_submitted: ["Не отправлен", "neutral"],
  pending: ["На проверке", "warning"],
  verified: ["Профиль проверен", "success"],
  rejected: ["Нужны уточнения", "danger"],
};

export const categoryLabels = {
  food: "Продукты питания",
  children: "Детские товары",
  medicine: "Лекарства",
  clothes: "Одежда",
  other: "Другое",
};

export function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
}

export function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "Сумма не указана";
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(Number(value))} ₽`;
}
