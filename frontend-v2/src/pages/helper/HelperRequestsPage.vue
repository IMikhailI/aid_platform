<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import HelperEmptyState from "../../components/helper/HelperEmptyState.vue";
import HelperFeedCard from "../../components/helper/HelperFeedCard.vue";
import HelperTakeModal from "../../components/helper/HelperTakeModal.vue";
import { getHelperApiError, getPublishedRequestsPage, takeRequest } from "../../services/helperApi";
import { isRequestSaved, removeSavedRequest, toggleSavedRequest } from "../../stores/helperSavedStore";

const router = useRouter();
const feed = ref({ count: 0, next: null, previous: null, results: [] });
const loading = ref(true);
const errorMessage = ref("");
const modalError = ref("");
const taking = ref(false);
const takeSucceeded = ref(false);
const selectedRequest = ref(null);
const search = ref("");
const category = ref("");
const region = ref("");
const ordering = ref("-created_at");
const currentPage = ref(1);
const pageSize = 8;

const categories = [
  { value: "", label: "Все категории", icon: "package-box.svg" },
  { value: "food", label: "Еда", icon: "store.svg" },
  { value: "medicine", label: "Лекарства", icon: "pill.svg" },
  { value: "children", label: "Детские товары", icon: "baby-face.svg" },
  { value: "clothes", label: "Одежда", icon: "shirt.svg" },
];

const regions = computed(() => [...new Set(feed.value.results.map((item) => item.region).filter(Boolean))].sort());
const visibleRequests = computed(() => region.value
  ? feed.value.results.filter((item) => item.region === region.value)
  : feed.value.results);
const urgentCount = computed(() => feed.value.results.filter((item) => Number(item.urgency) >= 4).length);
const totalPages = computed(() => Math.max(1, Math.ceil(feed.value.count / pageSize)));
const foundCount = computed(() => region.value ? visibleRequests.value.length : feed.value.count);

function categoryCount(value) {
  if (!value) return feed.value.results.length;
  return feed.value.results.filter((item) => item.category === value).length;
}

async function loadRequests() {
  loading.value = true;
  errorMessage.value = "";
  try {
    feed.value = await getPublishedRequestsPage({
      search: search.value || undefined,
      category: category.value || undefined,
      ordering: ordering.value,
      page: currentPage.value,
      page_size: pageSize,
    });
    if (region.value && !regions.value.includes(region.value)) region.value = "";
  } catch (error) {
    errorMessage.value = getHelperApiError(error, "Не удалось загрузить опубликованные заявки.");
  } finally {
    loading.value = false;
  }
}

async function selectCategory(value) {
  category.value = value;
  currentPage.value = 1;
  await loadRequests();
}

async function applyServerFilters() {
  currentPage.value = 1;
  await loadRequests();
}

async function changePage(page) {
  currentPage.value = page;
  await loadRequests();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function openTakeModal(request) {
  selectedRequest.value = request;
  modalError.value = "";
  takeSucceeded.value = false;
}

function closeTakeModal() {
  if (taking.value) return;
  selectedRequest.value = null;
  modalError.value = "";
  takeSucceeded.value = false;
}

async function confirmTake(method) {
  taking.value = true;
  modalError.value = "";
  try {
    const requestId = selectedRequest.value.id;
    await takeRequest(requestId, { method });
    feed.value.results = feed.value.results.filter((item) => item.id !== requestId);
    feed.value.count = Math.max(0, feed.value.count - 1);
    removeSavedRequest(requestId);
    takeSucceeded.value = true;
  } catch (error) {
    modalError.value = getHelperApiError(error);
  } finally {
    taking.value = false;
  }
}

onMounted(loadRequests);
</script>

<template>
  <section class="helper-page helper-requests-page">
    <header class="helper-page__heading">
      <h1>Заявки на помощь</h1>
      <p>Выберите запрос и окажите адресную помощь нуждающимся</p>
    </header>

    <div class="requests-feed-stats">
      <article><span><img src="/icons/package-box.svg" alt="" /></span><div><small>Активных заявок</small><strong>{{ feed.count }}</strong></div></article>
      <article><span><img src="/icons/clock.svg" alt="" /></span><div><small>Срочных на странице</small><strong>{{ urgentCount }}</strong></div></article>
      <article><span><img src="/icons/shield.svg" alt="" /></span><div><small>Проверенных НКО</small><strong>—</strong></div></article>
      <article><span><img src="/icons/trending-up.svg" alt="" /></span><div><small>Откликов сегодня</small><strong>—</strong></div></article>
    </div>

    <div class="requests-category-tabs" aria-label="Категории заявок">
      <button
        v-for="item in categories"
        :key="item.value"
        type="button"
        :class="{ 'requests-category-tabs__item--active': category === item.value }"
        @click="selectCategory(item.value)"
      >
        <img :src="`/icons/${item.icon}`" alt="" />
        {{ item.label }}
        <span v-if="item.value">{{ categoryCount(item.value) }}</span>
      </button>
    </div>

    <form class="requests-feed-filters" @submit.prevent="applyServerFilters">
      <label class="requests-feed-search"><img src="/icons/search.svg" alt="" /><input v-model.trim="search" type="search" placeholder="Поиск по названию или региону…" /></label>
      <select v-model="region" title="Frontend-фильтр по текущей странице" aria-label="Регион">
        <option value="">Все регионы</option>
        <option v-for="item in regions" :key="item" :value="item">{{ item }}</option>
      </select>
      <select v-model="ordering" aria-label="Сортировка" @change="applyServerFilters">
        <option value="-created_at">Сначала новые</option>
        <option value="-urgency">Сначала срочные</option>
        <option value="requested_amount">Сначала меньшая сумма</option>
        <option value="-requested_amount">Сначала большая сумма</option>
      </select>
      <button class="requests-filter-button" type="submit"><img src="/icons/filter.svg" alt="" /> Фильтры</button>
    </form>

    <p class="requests-feed-found">Найдено заявок: <strong>{{ foundCount }}</strong></p>
    <p v-if="errorMessage" class="helper-message helper-message--error" role="alert">{{ errorMessage }}</p>

    <div v-if="loading" class="requests-feed-loading" aria-live="polite">
      <span></span><p>Загружаем доступные заявки…</p>
    </div>
    <HelperEmptyState v-else-if="!visibleRequests.length" title="Нет доступных заявок" text="Попробуйте изменить фильтры или вернуться позже." />
    <div v-else class="requests-feed-grid">
      <HelperFeedCard
        v-for="request in visibleRequests"
        :key="request.id"
        :request="request"
        :saved="isRequestSaved(request.id)"
        @respond="openTakeModal"
        @toggle-save="toggleSavedRequest"
      />
    </div>

    <nav v-if="totalPages > 1" class="requests-pagination" aria-label="Страницы заявок">
      <button type="button" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">←</button>
      <button
        v-for="page in totalPages"
        :key="page"
        type="button"
        :class="{ 'requests-pagination__active': page === currentPage }"
        @click="changePage(page)"
      >{{ page }}</button>
      <button type="button" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">→</button>
    </nav>

    <HelperTakeModal
      :request="selectedRequest"
      :loading="taking"
      :error="modalError"
      :success="takeSucceeded"
      @close="closeTakeModal"
      @confirm="confirmTake"
      @go-my-help="router.push('/helper/my-help')"
    />
  </section>
</template>
