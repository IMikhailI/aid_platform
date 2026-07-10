<script setup>
import { computed, onMounted, ref } from "vue";
import ModeratorDecisionModal from "../../components/moderator/ModeratorDecisionModal.vue";
import ModeratorEmptyState from "../../components/moderator/ModeratorEmptyState.vue";
import ModeratorRequestCard from "../../components/moderator/ModeratorRequestCard.vue";
import ModeratorRequestDetailsModal from "../../components/moderator/ModeratorRequestDetailsModal.vue";
import ModeratorStatusTabs from "../../components/moderator/ModeratorStatusTabs.vue";
import ModeratorVerificationPanel from "../../components/moderator/ModeratorVerificationPanel.vue";
import { useModeratorCounts } from "../../components/moderator/useModeratorCounts";
import { decideModerationRequest, getModerationQueue, getModeratorApiError, getVerificationQueue, overrideFraud } from "../../services/moderatorApi";

const feed = ref({ count: 0, next: null, previous: null, results: [] });
const verifications = ref([]);
const loading = ref(true);
const verificationLoading = ref(true);
const actionLoading = ref(false);
const error = ref("");
const notice = ref("");
const modalError = ref("");
const selected = ref(null);
const decisionTarget = ref(null);
const decisionMode = ref("reject");
const search = ref("");
const category = ref("");
const flagged = ref("");
const ordering = ref("-created_at");
const currentPage = ref(1);
const pageSize = 10;

const flaggedCount = computed(() => feed.value.results.filter((item) => item.is_flagged).length);
const safePercent = computed(() => feed.value.results.length ? Math.round((feed.value.results.length - flaggedCount.value) / feed.value.results.length * 100) : 100);
const totalPages = computed(() => Math.max(1, Math.ceil(feed.value.count / pageSize)));
const { approvalPercent, counts, countsLoading, loadCounts } = useModeratorCounts();

async function loadQueue() {
  loading.value = true; error.value = "";
  try {
    feed.value = await getModerationQueue({ search: search.value || undefined, category: category.value || undefined, is_flagged: flagged.value || undefined, ordering: ordering.value, page: currentPage.value, page_size: pageSize });
  } catch (requestError) { error.value = getModeratorApiError(requestError, "Не удалось загрузить очередь"); }
  finally { loading.value = false; }
}

async function loadVerifications() {
  verificationLoading.value = true;
  try { verifications.value = (await getVerificationQueue({ status: "pending", ordering: "submitted_at" })).results; }
  catch { verifications.value = []; }
  finally { verificationLoading.value = false; }
}

async function approve(request) {
  actionLoading.value = true; error.value = ""; notice.value = "";
  try {
    await decideModerationRequest(request.id, "approve");
    notice.value = `Заявка #${request.id} одобрена и опубликована`;
    selected.value = null;
    await Promise.all([loadQueue(), loadCounts()]);
  } catch (requestError) { error.value = getModeratorApiError(requestError, "Не удалось одобрить заявку"); }
  finally { actionLoading.value = false; }
}

function openDecision(request, mode = "reject") {
  selected.value = null; decisionTarget.value = request; decisionMode.value = mode; modalError.value = "";
}

async function confirmDecision(payload) {
  actionLoading.value = true; modalError.value = ""; notice.value = "";
  try {
    if (decisionMode.value === "override") {
      await overrideFraud(decisionTarget.value.id, payload.newAction, payload.comment);
      notice.value = `Fraud override для заявки #${decisionTarget.value.id} сохранён`;
    } else {
      await decideModerationRequest(decisionTarget.value.id, "reject", payload.comment);
      notice.value = `Заявка #${decisionTarget.value.id} отклонена`;
      await Promise.all([loadQueue(), loadCounts()]);
    }
    decisionTarget.value = null;
  } catch (requestError) { modalError.value = getModeratorApiError(requestError); }
  finally { actionLoading.value = false; }
}

async function applyFilters() { currentPage.value = 1; await loadQueue(); }
async function changePage(page) { currentPage.value = page; await loadQueue(); window.scrollTo({ top: 0, behavior: "smooth" }); }
function verificationDecided(id) { verifications.value = verifications.value.filter((item) => item.id !== id); notice.value = "Решение по верификации сохранено"; }

onMounted(() => { loadQueue(); loadCounts(); loadVerifications(); });
</script>

<template>
  <section class="moderator-page">
    <div class="moderator-kpis">
      <article><span><img src="/icons/clock.svg" alt="" /></span><div><strong>{{ loading ? "—" : feed.count }}</strong><b>На модерации</b><small>Требуют проверки</small></div></article>
      <article><span><img src="/icons/check-circle.svg" alt="" /></span><div><strong>{{ countsLoading ? "—" : counts.approved }}</strong><b>Одобрено</b><small>Опубликованы, в работе или закрыты</small></div></article>
      <article><span><img src="/icons/x-circle.svg" alt="" /></span><div><strong>{{ countsLoading ? "—" : counts.rejected }}</strong><b>Отклонено</b><small>Архив отрицательных решений</small></div></article>
      <article><span><img src="/icons/trending-up.svg" alt="" /></span><div><strong>{{ countsLoading ? "—" : approvalPercent }}</strong><b>Процент одобрения</b><small>По принятым решениям</small></div></article>
    </div>

    <section class="moderator-queue-toolbar">
      <ModeratorStatusTabs :pending="countsLoading ? '—' : counts.pending" :approved="countsLoading ? '—' : counts.approved" :rejected="countsLoading ? '—' : counts.rejected" />
      <form @submit.prevent="applyFilters"><label><img src="/icons/search.svg" alt="" /><input v-model.trim="search" type="search" placeholder="Поиск по названию, описанию или региону…" /></label><select v-model="category" aria-label="Категория"><option value="">Все категории</option><option value="food">Еда</option><option value="children">Детские товары</option><option value="medicine">Лекарства</option><option value="clothes">Одежда</option><option value="other">Другое</option></select><select v-model="flagged" aria-label="Риск"><option value="">Любой риск</option><option value="true">Только с флагом</option><option value="false">Без флага</option></select><select v-model="ordering" aria-label="Сортировка"><option value="-created_at">Сначала новые</option><option value="-risk_score">Сначала рискованные</option><option value="risk_score">Сначала безопасные</option></select><button type="submit"><img src="/icons/filter.svg" alt="" /> Фильтры</button></form>
    </section>

    <p v-if="notice" class="moderator-message moderator-message--success">{{ notice }}</p>
    <p v-if="error" class="moderator-message moderator-message--error">{{ error }}</p>
    <div v-if="loading" class="moderator-page-loading"><span></span><p>Загружаем очередь модерации…</p></div>
    <ModeratorEmptyState v-else-if="!feed.results.length" title="Очередь пуста" text="Новых заявок на модерации сейчас нет." icon="check-circle.svg" />
    <div v-else class="moderator-request-list"><ModeratorRequestCard v-for="request in feed.results" :key="request.id" :request="request" :busy="actionLoading" @details="selected = $event" @approve="approve" @reject="openDecision" /></div>
    <nav v-if="totalPages > 1" class="moderator-pagination"><button type="button" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">←</button><button v-for="page in totalPages" :key="page" type="button" :class="{ active: page === currentPage }" @click="changePage(page)">{{ page }}</button><button type="button" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">→</button></nav>

    <section class="moderator-security">
      <header><span><img src="/icons/shield.svg" alt="" /></span><div><h2>Контроль безопасности</h2><p>Автоматическое выявление подозрительной активности</p></div></header>
      <div><article><img src="/icons/alert-triangle.svg" alt="" /><strong>{{ flaggedCount }}</strong><b>Заявок с флагом</b><small>В текущей странице очереди</small></article><article class="warning"><img src="/icons/flag.svg" alt="" /><strong>{{ feed.results.filter(item => item.risk_score >= 70).length }}</strong><b>Высокий уровень риска</b><small>Требуют дополнительной проверки</small></article><article><img src="/icons/check-circle.svg" alt="" /><strong>{{ safePercent }}%</strong><b>Без флагов</b><small>На текущей странице</small></article></div>
    </section>

    <ModeratorVerificationPanel :items="verifications" :loading="verificationLoading" @decided="verificationDecided" />
    <ModeratorRequestDetailsModal :request="selected" :action-loading="actionLoading" @close="selected = null" @approve="approve" @reject="openDecision" @override="openDecision($event, 'override')" />
    <ModeratorDecisionModal :request="decisionTarget" :mode="decisionMode" :loading="actionLoading" :error="modalError" @close="decisionTarget = null" @confirm="confirmDecision" />
  </section>
</template>
