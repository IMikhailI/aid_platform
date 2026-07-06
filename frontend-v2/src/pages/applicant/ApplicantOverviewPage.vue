<script setup>
import { computed, onMounted, ref } from "vue";
import { getApplicantProfile, getApplicantRequests, getApplicantApiError } from "../../services/applicantApi";
import { verificationStatus } from "../../components/applicant/applicantView";

const requests = ref([]);
const profile = ref(null);
const loading = ref(true);
const error = ref("");

const stats = computed(() => [
  { label: "Активных заявок", value: requests.value.filter((item) => !["closed", "rejected"].includes(item.status)).length, icon: "file-text.svg", tone: "blue" },
  { label: "На модерации", value: requests.value.filter((item) => item.status === "on_moderation").length, icon: "clock.svg", tone: "orange" },
  { label: "В работе", value: requests.value.filter((item) => ["published", "in_progress"].includes(item.status)).length, icon: "heart-outline.svg", tone: "violet" },
  { label: "Завершено", value: requests.value.filter((item) => item.status === "closed").length, icon: "check-circle.svg", tone: "green" },
]);
const verification = computed(() => verificationStatus[profile.value?.verification_status] || verificationStatus.not_submitted);

onMounted(async () => {
  try {
    [requests.value, profile.value] = await Promise.all([getApplicantRequests(), getApplicantProfile()]);
  } catch (requestError) {
    error.value = getApplicantApiError(requestError, "Не удалось загрузить обзор");
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="applicant-page applicant-overview">
    <header class="applicant-page__header"><div><h1>Личный кабинет</h1><p>Управляйте заявками и следите за статусом получения помощи</p></div></header>
    <p v-if="error" class="applicant-alert applicant-alert--error">{{ error }}</p>
    <div class="applicant-stats" :aria-busy="loading">
      <article v-for="stat in stats" :key="stat.label" class="applicant-stat-card">
        <span :class="`applicant-stat-card__icon applicant-stat-card__icon--${stat.tone}`"><img :src="`/icons/${stat.icon}`" alt="" /></span>
        <div><strong>{{ loading ? "—" : stat.value }}</strong><span>{{ stat.label }}</span></div>
      </article>
    </div>

    <article class="applicant-verification-card">
      <div class="applicant-verification-card__icon"><img src="/icons/shield.svg" alt="" /></div>
      <div><span>Статус профиля</span><h2>{{ loading ? "Загрузка…" : verification[0] }}</h2><p>Проверенный профиль помогает быстрее проходить модерацию заявок.</p></div>
      <RouterLink class="applicant-button applicant-button--light" to="/applicant/settings">Настроить профиль</RouterLink>
    </article>

    <section class="applicant-quick-actions">
      <h2>Быстрые действия</h2>
      <div class="applicant-quick-actions__grid">
        <RouterLink to="/applicant/requests"><span><img src="/icons/file-text.svg" alt="" /></span><div><strong>Мои заявки</strong><small>Создать заявку или проверить её статус</small></div><b>→</b></RouterLink>
        <RouterLink to="/applicant/history"><span><img src="/icons/heart-outline.svg" alt="" /></span><div><strong>История помощи</strong><small>Посмотреть завершённые заявки</small></div><b>→</b></RouterLink>
      </div>
    </section>
  </section>
</template>
