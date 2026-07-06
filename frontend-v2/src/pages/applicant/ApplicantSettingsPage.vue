<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { authStore } from "../../stores/authStore";
import {
  getApplicantApiError, getApplicantProfile, getApplicantVerificationHistory,
  submitApplicantVerification, updateApplicantProfile,
} from "../../services/applicantApi";
import { formatDate, verificationStatus } from "../../components/applicant/applicantView";

const profile = ref(null);
const history = ref([]);
const loading = ref(true);
const saving = ref(false);
const submitting = ref(false);
const error = ref("");
const notice = ref("");
const form = reactive({ household_size: 1, dependents_count: 0, consent_to_data_processing: false });
const status = computed(() => verificationStatus[profile.value?.verification_status] || verificationStatus.not_submitted);
const region = computed(() => profile.value?.region || authStore.currentUser.value?.region || "");
const canSubmit = computed(() => profile.value && region.value.trim() && !["pending", "verified"].includes(profile.value.verification_status) && form.consent_to_data_processing);

function fillForm(data) {
  form.household_size = data.household_size;
  form.dependents_count = data.dependents_count;
  form.consent_to_data_processing = data.consent_to_data_processing;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [profileData, historyData] = await Promise.all([getApplicantProfile(), getApplicantVerificationHistory()]);
    profile.value = profileData;
    history.value = historyData;
    fillForm(profileData);
  } catch (requestError) { error.value = getApplicantApiError(requestError, "Не удалось загрузить профиль"); }
  finally { loading.value = false; }
}

async function save() {
  error.value = ""; notice.value = ""; saving.value = true;
  try {
    profile.value = await updateApplicantProfile({ ...form });
    fillForm(profile.value);
    notice.value = "Изменения сохранены";
  } catch (requestError) { error.value = getApplicantApiError(requestError, "Не удалось сохранить профиль"); }
  finally { saving.value = false; }
}

async function submitVerification() {
  if (!canSubmit.value) return;
  error.value = ""; notice.value = ""; submitting.value = true;
  try {
    await updateApplicantProfile({ ...form });
    await submitApplicantVerification();
    notice.value = "Профиль отправлен на проверку";
    await load();
  } catch (requestError) { error.value = getApplicantApiError(requestError, "Не удалось отправить профиль на проверку"); }
  finally { submitting.value = false; }
}

onMounted(load);
</script>

<template>
  <section class="applicant-page applicant-settings">
    <header class="applicant-page__header"><div><h1>Настройки профиля</h1><p>Управляйте данными профиля и статусом проверки</p></div></header>
    <p v-if="notice" class="applicant-alert applicant-alert--success">{{ notice }}</p>
    <p v-if="error" class="applicant-alert applicant-alert--error">{{ error }}</p>

    <form class="applicant-settings-card" :aria-busy="loading" @submit.prevent="save">
      <div class="applicant-settings-card__heading"><span><img src="/icons/user.svg" alt="" /></span><div><h2>Данные профиля</h2><p>Основная информация вашей учётной записи</p></div></div>
      <div class="applicant-form applicant-settings-form">
        <div class="applicant-form__row">
          <label>Имя пользователя<input :value="authStore.currentUser.value?.username || ''" disabled /></label>
          <label>Email<input :value="authStore.currentUser.value?.email || ''" disabled /></label>
        </div>
        <div class="applicant-form__row">
          <label>Роль<input value="Получатель помощи" disabled /></label>
          <label>Регион<input :value="region" disabled /><small>Регион задаётся данными учётной записи</small></label>
        </div>
        <div class="applicant-form__row">
          <label>Человек в семье<input v-model.number="form.household_size" type="number" min="1" required /></label>
          <label>Количество иждивенцев<input v-model.number="form.dependents_count" type="number" min="0" required /></label>
        </div>
        <label class="applicant-checkbox"><input v-model="form.consent_to_data_processing" type="checkbox" /><span>Я согласен на обработку персональных данных</span></label>
      </div>
      <div class="applicant-settings-card__footer"><button class="applicant-button" type="submit" :disabled="loading || saving">{{ saving ? "Сохраняем…" : "Сохранить изменения" }}</button></div>
    </form>

    <section class="applicant-settings-card applicant-verification-section">
      <div class="applicant-settings-card__heading"><span><img src="/icons/shield.svg" alt="" /></span><div><h2>Проверка профиля</h2><p>Статус подтверждения данных получателя помощи</p></div></div>
      <div class="applicant-verification-status">
        <span :class="`applicant-pill applicant-pill--${status[1]}`">{{ loading ? "Загрузка…" : status[0] }}</span>
        <p v-if="profile?.verification_status === 'verified'">Профиль успешно проверен.</p>
        <p v-else-if="profile?.verification_status === 'pending'">Данные переданы на проверку. Дождитесь результата.</p>
        <p v-else-if="!region">Чтобы отправить профиль на проверку, сначала укажите регион в данных учётной записи.</p>
        <p v-else-if="!form.consent_to_data_processing">Для отправки на проверку необходимо согласие на обработку персональных данных.</p>
        <p v-else>Заполните профиль и отправьте его на проверку.</p>
        <button v-if="!['pending', 'verified'].includes(profile?.verification_status)" class="applicant-button" type="button" :disabled="!canSubmit || submitting" @click="submitVerification">{{ submitting ? "Отправляем…" : "Отправить на проверку" }}</button>
      </div>
      <div v-if="history.length" class="applicant-verification-history">
        <h3>История проверок</h3>
        <div v-for="item in history" :key="item.id"><span :class="`applicant-pill applicant-pill--${(verificationStatus[item.status] || verificationStatus.not_submitted)[1]}`">{{ (verificationStatus[item.status] || [item.status])[0] }}</span><time>{{ formatDate(item.submitted_at) }}</time></div>
      </div>
    </section>
  </section>
</template>
