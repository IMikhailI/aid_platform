<script setup>
import { reactive, ref } from "vue";
import { createApplicantRequest, getApplicantApiError } from "../../services/applicantApi";

const props = defineProps({ region: { type: String, default: "" } });
const emit = defineEmits(["close", "created"]);
const submitting = ref(false);
const error = ref("");
const form = reactive({
  category: "food",
  title: "",
  description: "",
  region: props.region,
  requested_amount: "",
  urgency: 3,
});

async function submit() {
  error.value = "";
  if (!form.title.trim() || !form.description.trim() || !form.region.trim()) {
    error.value = "Заполните название, описание и регион";
    return;
  }
  submitting.value = true;
  try {
    const payload = { ...form, title: form.title.trim(), description: form.description.trim(), region: form.region.trim() };
    if (!payload.requested_amount) delete payload.requested_amount;
    const request = await createApplicantRequest(payload);
    emit("created", request);
  } catch (requestError) {
    error.value = getApplicantApiError(requestError, "Не удалось создать заявку");
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="applicant-modal" role="presentation" @mousedown.self="emit('close')">
    <section class="applicant-modal__card" role="dialog" aria-modal="true" aria-labelledby="create-request-title">
      <button class="applicant-modal__close" type="button" aria-label="Закрыть" @click="emit('close')">×</button>
      <h2 id="create-request-title">Новая заявка</h2>
      <p>Расскажите, какая помощь вам необходима</p>

      <form class="applicant-form" @submit.prevent="submit">
        <label>Категория
          <select v-model="form.category">
            <option value="food">Продукты питания</option><option value="children">Детские товары</option>
            <option value="medicine">Лекарства</option><option value="clothes">Одежда</option><option value="other">Другое</option>
          </select>
        </label>
        <label>Название заявки
          <input v-model="form.title" maxlength="180" placeholder="Кратко опишите, что требуется" required />
        </label>
        <label>Подробное описание
          <textarea v-model="form.description" rows="4" placeholder="Укажите важные детали" required></textarea>
        </label>
        <div class="applicant-form__row">
          <label>Регион<input v-model="form.region" maxlength="120" required /></label>
          <label>Необходимая сумма, ₽<input v-model="form.requested_amount" type="number" min="0" step="0.01" placeholder="Необязательно" /></label>
        </div>
        <label>Срочность: {{ form.urgency }} из 5<input v-model.number="form.urgency" type="range" min="1" max="5" /></label>
        <p v-if="error" class="applicant-alert applicant-alert--error">{{ error }}</p>
        <div class="applicant-modal__actions">
          <button class="applicant-button applicant-button--secondary" type="button" @click="emit('close')">Отмена</button>
          <button class="applicant-button" type="submit" :disabled="submitting">{{ submitting ? "Отправляем…" : "Создать заявку" }}</button>
        </div>
      </form>
    </section>
  </div>
</template>
