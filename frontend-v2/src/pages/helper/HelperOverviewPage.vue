<script setup>
import { computed, onMounted, ref } from "vue";
import HelperEmptyState from "../../components/helper/HelperEmptyState.vue";
import { savedRequestIds } from "../../stores/helperSavedStore";
import { authStore } from "../../stores/authStore";
import { getHelperApiError, getMyHelp } from "../../services/helperApi";

const myHelp = ref([]);
const loadingStats = ref(true);
const statsError = ref("");

const inProgressCount = computed(() => myHelp.value.filter((item) => {
  if (item.request_status !== "in_progress") return false;
  return ["none", "created", "delivered"].includes(item.fulfillment_status);
}).length);

const completedCount = computed(() => myHelp.value.filter((item) => (
  item.request_status === "closed" || item.fulfillment_status === "confirmed"
)).length);

onMounted(async () => {
  try {
    const page = await getMyHelp({ page_size: 100 });
    myHelp.value = page.results || [];
  } catch (requestError) {
    statsError.value = getHelperApiError(requestError, "Не удалось загрузить статистику помощи.");
  } finally {
    loadingStats.value = false;
  }
});
</script>

<template>
  <section class="helper-page">
    <header class="helper-page__heading">
      <h1>Добро пожаловать, {{ authStore.currentUser.value?.username || "помощник" }}!</h1>
      <p>Просматривайте историю оказанной помощи и находите новые запросы</p>
    </header>

    <div class="helper-stats">
      <article><span class="helper-stat-icon helper-stat-icon--purple">♡</span><h2>Оказано помощи</h2><strong>{{ loadingStats ? "—" : completedCount }}</strong></article>
      <article><span class="helper-stat-icon helper-stat-icon--blue">◷</span><h2>В процессе</h2><strong>{{ loadingStats ? "—" : inProgressCount }}</strong></article>
      <article>
        <span class="helper-stat-icon helper-stat-icon--yellow"><img src="/icons/bookmark.svg" alt="" /></span>
        <h2>Сохранено</h2>
        <strong>{{ savedRequestIds.length }}</strong>
      </article>
    </div>
    <p v-if="statsError" class="helper-message helper-message--error">{{ statsError }}</p>

    <section class="helper-panel helper-activity">
      <h2>Последняя активность</h2>
      <HelperEmptyState title="История помощи доступна в разделе «Моя помощь»" text="Откройте взятые заявки, чтобы создать сертификат, отметить передачу или проверить подтверждение." />
    </section>
  </section>
</template>
