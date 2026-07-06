<script setup>
import { onMounted, ref } from "vue";
import HelperEmptyState from "../../components/helper/HelperEmptyState.vue";
import HelperRequestCard from "../../components/helper/HelperRequestCard.vue";
import { getHelperApiError, getPublishedRequests, takeRequest } from "../../services/helperApi";
import { isRequestSaved, toggleSavedRequest } from "../../stores/helperSavedStore";

const requests = ref([]);
const loading = ref(true);
const errorMessage = ref("");
const successMessage = ref("");
const takingId = ref(null);
const search = ref("");
const category = ref("");

async function loadRequests() {
  loading.value = true;
  errorMessage.value = "";
  try {
    requests.value = await getPublishedRequests({
      search: search.value || undefined,
      category: category.value || undefined,
      page_size: 12,
    });
  } catch (error) {
    errorMessage.value = getHelperApiError(error, "Не удалось загрузить опубликованные заявки.");
  } finally {
    loading.value = false;
  }
}

async function handleTake(requestId) {
  takingId.value = requestId;
  errorMessage.value = "";
  successMessage.value = "";
  try {
    await takeRequest(requestId);
    requests.value = requests.value.filter((item) => item.id !== requestId);
    successMessage.value = "Заявка принята в работу.";
  } catch (error) {
    errorMessage.value = getHelperApiError(error);
  } finally {
    takingId.value = null;
  }
}

onMounted(loadRequests);
</script>

<template>
  <section class="helper-page">
    <header class="helper-page__heading helper-page__heading--row">
      <div><h1>Заявки на помощь</h1><p>Опубликованные запросы, доступные для отклика</p></div>
      <form class="helper-filters" @submit.prevent="loadRequests">
        <input v-model.trim="search" type="search" placeholder="Поиск" aria-label="Поиск заявок" />
        <select v-model="category" aria-label="Категория">
          <option value="">Все категории</option>
          <option value="food">Еда</option><option value="children">Детские товары</option>
          <option value="medicine">Лекарства</option><option value="clothes">Одежда</option><option value="other">Другое</option>
        </select>
        <button class="helper-primary-button" type="submit">Найти</button>
      </form>
    </header>

    <p v-if="successMessage" class="helper-message helper-message--success" role="status">{{ successMessage }}</p>
    <p v-if="errorMessage" class="helper-message helper-message--error" role="alert">{{ errorMessage }}</p>
    <div v-if="loading" class="helper-loading">Загружаем заявки…</div>
    <HelperEmptyState v-else-if="!requests.length" title="Нет доступных заявок" text="Попробуйте изменить фильтры или вернуться позже." />
    <div v-else class="helper-request-list">
      <HelperRequestCard
        v-for="request in requests"
        :key="request.id"
        :request="request"
        :saved="isRequestSaved(request.id)"
        :busy="takingId === request.id"
        @take="handleTake"
        @toggle-save="toggleSavedRequest"
      />
    </div>
  </section>
</template>
