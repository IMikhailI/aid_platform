<script setup>
import { computed, onMounted, ref } from "vue";
import HelperEmptyState from "../../components/helper/HelperEmptyState.vue";
import HelperRequestCard from "../../components/helper/HelperRequestCard.vue";
import { getHelperApiError, getPublishedRequests, takeRequest } from "../../services/helperApi";
import { removeSavedRequest, savedRequestIds } from "../../stores/helperSavedStore";

const published = ref([]);
const loading = ref(true);
const errorMessage = ref("");
const takingId = ref(null);
const savedRequests = computed(() => published.value.filter((item) => savedRequestIds.value.includes(Number(item.id))));

async function loadSaved() {
  loading.value = true;
  try {
    published.value = await getPublishedRequests({ page_size: 100 });
  } catch (error) {
    errorMessage.value = getHelperApiError(error, "Не удалось загрузить сохранённые заявки.");
  } finally {
    loading.value = false;
  }
}

async function handleTake(requestId) {
  takingId.value = requestId;
  errorMessage.value = "";
  try {
    await takeRequest(requestId);
    removeSavedRequest(requestId);
    published.value = published.value.filter((item) => item.id !== requestId);
  } catch (error) {
    errorMessage.value = getHelperApiError(error);
  } finally {
    takingId.value = null;
  }
}

onMounted(loadSaved);
</script>

<template>
  <section class="helper-page">
    <header class="helper-page__heading">
      <h1>Сохранённые заявки</h1>
      <p>Запросы, которые вы отметили для себя</p>
    </header>

    <p v-if="errorMessage" class="helper-message helper-message--error" role="alert">{{ errorMessage }}</p>
    <div v-if="loading" class="helper-loading">Загружаем сохранённые заявки…</div>
    <HelperEmptyState v-else-if="!savedRequests.length" title="Сохранённых заявок пока нет" text="Добавьте заявку из раздела «Заявки на помощь». Список хранится только в этом браузере." />
    <div v-else class="helper-request-list">
      <HelperRequestCard
        v-for="request in savedRequests"
        :key="request.id"
        :request="request"
        saved
        :busy="takingId === request.id"
        @take="handleTake"
        @toggle-save="removeSavedRequest"
      />
    </div>
  </section>
</template>
