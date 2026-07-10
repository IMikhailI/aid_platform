<script setup>
import { computed, onMounted, ref } from "vue";
import ModeratorEmptyState from "../../components/moderator/ModeratorEmptyState.vue";
import ModeratorRequestCard from "../../components/moderator/ModeratorRequestCard.vue";
import ModeratorRequestDetailsModal from "../../components/moderator/ModeratorRequestDetailsModal.vue";
import ModeratorStatusTabs from "../../components/moderator/ModeratorStatusTabs.vue";
import { useModeratorCounts } from "../../components/moderator/useModeratorCounts";
import { getModerationRequests, getModeratorApiError } from "../../services/moderatorApi";

const feed = ref({ count: 0, next: null, previous: null, results: [] });
const loading = ref(true);
const error = ref("");
const selected = ref(null);
const search = ref("");
const category = ref("");
const region = ref("");
const ordering = ref("-updated_at");
const currentPage = ref(1);
const pageSize = 10;

const totalPages = computed(() => Math.max(1, Math.ceil(feed.value.count / pageSize)));
const flaggedCount = computed(() => feed.value.results.filter((item) => item.is_flagged).length);
const commentedCount = computed(() => feed.value.results.filter((item) => item.latest_moderation_comment).length);
const { counts, countsLoading, loadCounts } = useModeratorCounts();

async function loadRequests() {
  loading.value = true; error.value = "";
  try {
    feed.value = await getModerationRequests({
      status: "rejected",
      search: search.value || undefined,
      category: category.value || undefined,
      region: region.value || undefined,
      ordering: ordering.value,
      page: currentPage.value,
      page_size: pageSize,
    });
  } catch (requestError) {
    error.value = getModeratorApiError(requestError, "Не удалось загрузить отклонённые заявки");
  } finally {
    loading.value = false;
  }
}

async function applyFilters() { currentPage.value = 1; await loadRequests(); }
async function changePage(page) { currentPage.value = page; await loadRequests(); window.scrollTo({ top: 0, behavior: "smooth" }); }

onMounted(() => { loadRequests(); loadCounts(); });
</script>

<template>
  <section class="moderator-page">
    <div class="moderator-kpis">
      <article><span><img src="/icons/x-circle.svg" alt="" /></span><div><strong>{{ loading ? "—" : feed.count }}</strong><b>Отклонённые</b><small>Архив решений</small></div></article>
      <article><span><img src="/icons/flag.svg" alt="" /></span><div><strong>{{ loading ? "—" : flaggedCount }}</strong><b>С флагом</b><small>На текущей странице</small></div></article>
      <article><span><img src="/icons/file-text.svg" alt="" /></span><div><strong>{{ loading ? "—" : commentedCount }}</strong><b>С комментарием</b><small>Есть причина решения</small></div></article>
      <article><span><img src="/icons/clock.svg" alt="" /></span><div><strong>{{ pageSize }}</strong><b>На странице</b><small>Размер текущей выборки</small></div></article>
    </div>

    <section class="moderator-queue-toolbar">
      <ModeratorStatusTabs :pending="countsLoading ? '—' : counts.pending" :approved="countsLoading ? '—' : counts.approved" :rejected="countsLoading ? '—' : counts.rejected" />
      <form @submit.prevent="applyFilters"><label><img src="/icons/search.svg" alt="" /><input v-model.trim="search" type="search" placeholder="Поиск по названию, описанию или региону…" /></label><label><input v-model.trim="region" type="search" placeholder="Регион" /></label><select v-model="category" aria-label="Категория"><option value="">Все категории</option><option value="food">Еда</option><option value="children">Детские товары</option><option value="medicine">Лекарства</option><option value="clothes">Одежда</option><option value="other">Другое</option></select><select v-model="ordering" aria-label="Сортировка"><option value="-updated_at">Сначала обновлённые</option><option value="-created_at">Сначала новые</option><option value="-risk_score">Сначала рискованные</option><option value="-urgency">Сначала срочные</option></select><button type="submit"><img src="/icons/filter.svg" alt="" /> Фильтры</button></form>
    </section>

    <p v-if="error" class="moderator-message moderator-message--error">{{ error }}</p>
    <div v-if="loading" class="moderator-page-loading"><span></span><p>Загружаем отклонённые заявки…</p></div>
    <ModeratorEmptyState v-else-if="!feed.results.length" title="Отклонённых заявок нет" text="Здесь будут заявки, по которым принято отрицательное решение." icon="x-circle.svg" />
    <div v-else class="moderator-request-list"><ModeratorRequestCard v-for="request in feed.results" :key="request.id" :request="request" :actions="false" @details="selected = $event" /></div>
    <nav v-if="totalPages > 1" class="moderator-pagination"><button type="button" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">←</button><button v-for="page in totalPages" :key="page" type="button" :class="{ active: page === currentPage }" @click="changePage(page)">{{ page }}</button><button type="button" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">→</button></nav>

    <ModeratorRequestDetailsModal :request="selected" :actions="false" @close="selected = null" />
  </section>
</template>
