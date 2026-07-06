<script setup>
import { computed } from "vue";

const props = defineProps({
  request: { type: Object, required: true },
  saved: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  showSave: { type: Boolean, default: true },
});

defineEmits(["take", "toggle-save"]);

const categories = {
  food: "Еда",
  children: "Детские товары",
  medicine: "Лекарства",
  clothes: "Одежда",
  other: "Другое",
};

const category = computed(() => categories[props.request.category] || "Другое");
const amount = computed(() => {
  const value = Number(props.request.requested_amount);
  return Number.isFinite(value) ? `${new Intl.NumberFormat("ru-RU").format(value)} ₽` : "Сумма не указана";
});
const date = computed(() => new Intl.DateTimeFormat("ru-RU", {
  day: "numeric",
  month: "long",
  year: "numeric",
}).format(new Date(props.request.created_at)));
</script>

<template>
  <article class="helper-request-card">
    <span class="helper-request-card__icon"><img src="/icons/package-box.svg" alt="" /></span>
    <div class="helper-request-card__body">
      <h3>{{ request.title }}</h3>
      <div class="helper-request-card__meta">
        <span>◇ {{ category }}</span>
        <span>⌖ {{ request.region }}</span>
        <span>▣ {{ date }}</span>
      </div>
      <strong class="helper-request-card__amount">{{ amount }}</strong>
    </div>
    <div class="helper-request-card__actions">
      <button class="helper-primary-button" type="button" :disabled="busy" @click="$emit('take', request.id)">
        {{ busy ? "Отправляем…" : "Откликнуться" }}
      </button>
      <button
        v-if="showSave"
        class="helper-save-button"
        :class="{ 'helper-save-button--active': saved }"
        type="button"
        :aria-label="saved ? 'Удалить из сохранённых' : 'Сохранить заявку'"
        @click="$emit('toggle-save', request.id)"
      >
        <img src="/icons/bookmark.svg" alt="" />
      </button>
    </div>
  </article>
</template>
