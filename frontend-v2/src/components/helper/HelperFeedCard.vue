<script setup>
import { computed } from "vue";

const props = defineProps({
  request: { type: Object, required: true },
  saved: { type: Boolean, default: false },
});

defineEmits(["respond", "toggle-save"]);

const categoryNames = {
  food: "Еда",
  children: "Детские товары",
  medicine: "Лекарства",
  clothes: "Одежда",
  other: "Другое",
};

const categoryIcons = {
  food: "store.svg",
  children: "baby-face.svg",
  medicine: "pill.svg",
  clothes: "shirt.svg",
  other: "package-box.svg",
};

const category = computed(() => categoryNames[props.request.category] || categoryNames.other);
const categoryIcon = computed(() => categoryIcons[props.request.category] || categoryIcons.other);
const isUrgent = computed(() => Number(props.request.urgency) >= 4);
const amount = computed(() => {
  const value = Number(props.request.requested_amount);
  return Number.isFinite(value) ? `${new Intl.NumberFormat("ru-RU").format(value)} ₽` : "Не указана";
});
const date = computed(() => new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
}).format(new Date(props.request.created_at)));
</script>

<template>
  <article class="requests-feed-card">
    <div class="requests-feed-card__top">
      <span class="requests-feed-card__category-icon"><img :src="`/icons/${categoryIcon}`" alt="" /></span>
      <div class="requests-feed-card__tags">
        <span class="requests-feed-card__category">{{ category }}</span>
        <span class="requests-feed-card__region">⌖ {{ request.region }}</span>
      </div>
      <span class="requests-feed-card__urgency" :class="{ 'requests-feed-card__urgency--high': isUrgent }">
        {{ isUrgent ? "Срочно" : "Актуально" }}
      </span>
      <button
        class="requests-feed-card__save"
        :class="{ 'requests-feed-card__save--active': saved }"
        type="button"
        :aria-label="saved ? 'Удалить из сохранённых' : 'Сохранить заявку'"
        @click="$emit('toggle-save', request.id)"
      >
        <img src="/icons/bookmark.svg" alt="" />
      </button>
    </div>

    <h2>{{ request.title }}</h2>
    <p class="requests-feed-card__privacy">Описание скрыто privacy-safe контрактом помощника.</p>

    <div class="requests-feed-card__details">
      <div><span>Примерный бюджет</span><strong>{{ amount }}</strong></div>
      <div class="requests-feed-card__date"><span>Опубликовано</span><strong>{{ date }}</strong></div>
    </div>

    <button class="requests-feed-card__respond" type="button" @click="$emit('respond', request)">
      Откликнуться на заявку <span aria-hidden="true">→</span>
    </button>
  </article>
</template>
