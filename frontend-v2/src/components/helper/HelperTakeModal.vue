<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  request: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  success: { type: Boolean, default: false },
});

const emit = defineEmits(["close", "confirm", "go-my-help"]);
const method = ref("cart");

const categoryNames = {
  food: "Еда",
  children: "Детские товары",
  medicine: "Лекарства",
  clothes: "Одежда",
  other: "Другое",
};

const amount = computed(() => {
  const value = Number(props.request?.requested_amount);
  return Number.isFinite(value) ? `${new Intl.NumberFormat("ru-RU").format(value)} ₽` : "Не указана";
});

watch(() => props.request?.id, () => { method.value = "cart"; });
</script>

<template>
  <div v-if="request" class="helper-take-overlay" role="presentation" @mousedown.self="emit('close')">
    <section v-if="!success" class="helper-take-dialog" role="dialog" aria-modal="true" aria-labelledby="take-dialog-title">
      <header class="helper-take-dialog__header">
        <div>
          <span>Отклик на заявку #{{ request.id }}</span>
          <h2 id="take-dialog-title">{{ request.title }}</h2>
          <p>{{ categoryNames[request.category] || "Другое" }} · {{ request.region }}</p>
        </div>
        <button type="button" aria-label="Закрыть" @click="emit('close')">×</button>
      </header>

      <div class="helper-take-dialog__content">
        <div class="helper-take-dialog__summary">
          <span>Примерный бюджет</span>
          <strong>{{ amount }}</strong>
          <small>Сумма ориентировочная; take не создаёт платёж или сертификат.</small>
        </div>

        <fieldset class="helper-methods">
          <legend>Как вы хотите помочь</legend>
          <label :class="{ 'helper-method--active': method === 'cart' }">
            <input v-model="method" type="radio" value="cart" />
            <img src="/icons/package-box.svg" alt="" />
            <span><strong>Готовая корзина</strong><small>Набор необходимых товаров</small></span>
          </label>
          <label :class="{ 'helper-method--active': method === 'certificate' }">
            <input v-model="method" type="radio" value="certificate" />
            <img src="/icons/bookmark.svg" alt="" />
            <span><strong>Сертификат</strong><small>Способ помощи будет уточнён позднее</small></span>
          </label>
          <label :class="{ 'helper-method--active': method === 'invoice' }">
            <input v-model="method" type="radio" value="invoice" />
            <img src="/icons/pill.svg" alt="" />
            <span><strong>Счёт или аптека</strong><small>Оплата заявленной потребности</small></span>
          </label>
        </fieldset>

        <div class="helper-take-privacy">
          <strong>Конфиденциальность</strong>
          <p>Персональные данные заявителя скрыты. Отклик означает принятие заявки в работу.</p>
        </div>

        <p v-if="error" class="helper-message helper-message--error" role="alert">{{ error }}</p>
        <div class="helper-take-dialog__actions">
          <button class="helper-secondary-button" type="button" :disabled="loading" @click="emit('close')">Отмена</button>
          <button class="helper-primary-button" type="button" :disabled="loading" @click="emit('confirm', method)">
            {{ loading ? "Отправляем…" : "Взять в работу" }}
          </button>
        </div>
      </div>
    </section>

    <section v-else class="helper-success-dialog" role="dialog" aria-modal="true" aria-labelledby="take-success-title">
      <span class="helper-success-dialog__icon">✓</span>
      <h2 id="take-success-title">Спасибо!</h2>
      <p>Заявка принята в работу и удалена из доступной ленты.</p>
      <div class="helper-success-dialog__actions">
        <button class="helper-primary-button" type="button" @click="emit('go-my-help')">Перейти в «Моя помощь»</button>
        <button class="helper-secondary-button" type="button" @click="emit('close')">Вернуться к заявкам</button>
      </div>
    </section>
  </div>
</template>
