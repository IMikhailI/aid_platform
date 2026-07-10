<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import HelperEmptyState from "../../components/helper/HelperEmptyState.vue";
import {
  createFulfillment, deliverFulfillment, getHelperApiError, getMyHelp,
} from "../../services/helperApi";

const feed = ref({ count: 0, next: null, previous: null, results: [] });
const loading = ref(true);
const actionLoading = ref(false);
const error = ref("");
const modalError = ref("");
const notice = ref("");
const selected = ref(null);
const expanded = ref(new Set());
const currentPage = ref(1);
const pageSize = 10;
const form = reactive({ provider_name: "", amount: "" });

const totalPages = computed(() => Math.max(1, Math.ceil(feed.value.count / pageSize)));
const waitingCount = computed(() => feed.value.results.filter((item) => (
  item.request_status === "in_progress"
  && ["none", "created", "delivered"].includes(item.fulfillment_status)
)).length);
const completedCount = computed(() => feed.value.results.filter((item) => (
  item.request_status === "closed" || item.fulfillment_status === "confirmed"
)).length);

const requestStatuses = {
  in_progress: "В работе",
  closed: "Закрыта",
};
const fulfillmentStatuses = {
  none: "Сертификат не создан",
  created: "Подготовлен",
  delivered: "Передан заявителю",
  confirmed: "Получение подтверждено",
};
const categories = {
  food: "Еда", children: "Детские товары", medicine: "Лекарства",
  clothes: "Одежда", other: "Другое",
};

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "Не указана";
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 }).format(Number(value))} ₽`;
}
function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(new Date(value));
}

async function load() {
  loading.value = true;
  error.value = "";
  try { feed.value = await getMyHelp({ page: currentPage.value, page_size: pageSize }); }
  catch (requestError) { error.value = getHelperApiError(requestError, "Не удалось загрузить вашу помощь."); }
  finally { loading.value = false; }
}

function openCreate(item) {
  selected.value = item;
  form.provider_name = "";
  form.amount = item.requested_amount || "";
  modalError.value = "";
}

async function submitCertificate() {
  if (!selected.value) return;
  modalError.value = "";
  if (!form.provider_name.trim() || !form.amount) {
    modalError.value = "Укажите поставщика и сумму сертификата.";
    return;
  }
  actionLoading.value = true;
  try {
    await createFulfillment(selected.value.request_id, {
      provider_name: form.provider_name.trim(), amount: form.amount,
    });
    notice.value = `Сертификат для заявки #${selected.value.request_id} создан`;
    selected.value = null;
    await load();
  } catch (requestError) { modalError.value = getHelperApiError(requestError, "Не удалось создать сертификат."); }
  finally { actionLoading.value = false; }
}

async function deliver(item) {
  actionLoading.value = true;
  error.value = "";
  try {
    await deliverFulfillment(item.request_id);
    notice.value = `Сертификат по заявке #${item.request_id} отмечен как переданный`;
    await load();
  } catch (requestError) { error.value = getHelperApiError(requestError, "Не удалось отметить передачу сертификата."); }
  finally { actionLoading.value = false; }
}

function toggleDetails(requestId) {
  const next = new Set(expanded.value);
  if (next.has(requestId)) next.delete(requestId); else next.add(requestId);
  expanded.value = next;
}
async function changePage(page) { currentPage.value = page; await load(); window.scrollTo({ top: 0, behavior: "smooth" }); }

onMounted(load);
</script>

<template>
  <section class="helper-page helper-my-help-page">
    <header class="helper-page__heading"><h1>Моя помощь</h1><p>Взятые заявки и передача демонстрационных сертификатов</p></header>

    <div class="helper-summary-cards">
      <article><span>Всего взято заявок</span><strong>{{ loading ? "—" : feed.count }}</strong></article>
      <article><span>В процессе</span><strong>{{ loading ? "—" : waitingCount }}</strong></article>
      <article><span>Оказано помощи</span><strong>{{ loading ? "—" : completedCount }}</strong></article>
    </div>

    <p v-if="notice" class="helper-message helper-message--success">{{ notice }}</p>
    <p v-if="error" class="helper-message helper-message--error">{{ error }}</p>
    <div v-if="loading" class="helper-my-help-loading"><span></span><p>Загружаем взятые заявки…</p></div>
    <HelperEmptyState v-else-if="!feed.results.length" title="Здесь появится ваша помощь" text="Возьмите опубликованную заявку в работу — она появится в этом разделе." />

    <div v-else class="helper-owned-list">
      <article v-for="item in feed.results" :key="item.request_id" class="helper-owned-card">
        <header>
          <div><small>Заявка #{{ item.request_id }} · {{ categories[item.category] || item.category }}</small><h2>{{ item.title }}</h2><p>⌖ {{ item.region }} · взята {{ formatDate(item.taken_at) }}</p></div>
          <span :class="`helper-owned-status helper-owned-status--${item.fulfillment_status}`">{{ fulfillmentStatuses[item.fulfillment_status] }}</span>
        </header>
        <div class="helper-owned-card__facts">
          <div><span>Бюджет заявки</span><strong>{{ formatMoney(item.requested_amount) }}</strong></div>
          <div><span>Статус заявки</span><strong>{{ requestStatuses[item.request_status] || item.request_status }}</strong></div>
          <div><span>Срочность</span><strong>{{ item.urgency }} из 5</strong></div>
        </div>
        <div v-if="expanded.has(item.request_id)" class="helper-owned-details">
          <div><span>Способ помощи</span><strong>{{ item.commitment_method }}</strong></div>
          <div><span>Комментарий</span><strong>{{ item.commitment_note || "Не указан" }}</strong></div>
          <template v-if="item.fulfillment_status !== 'none'">
            <div><span>Поставщик</span><strong>{{ item.provider_name }}</strong></div>
            <div><span>Сумма сертификата</span><strong>{{ formatMoney(item.fulfillment_amount) }}</strong></div>
            <div class="helper-owned-details__code"><span>Безопасный код</span><code>{{ item.masked_certificate_code }}</code></div>
          </template>
        </div>
        <footer>
          <button class="helper-owned-details-button" type="button" @click="toggleDetails(item.request_id)">{{ expanded.has(item.request_id) ? "Скрыть детали" : "Открыть заявку" }}</button>
          <button v-if="item.fulfillment_status === 'none'" class="helper-owned-primary" type="button" :disabled="actionLoading" @click="openCreate(item)">Создать сертификат</button>
          <button v-else-if="item.fulfillment_status === 'created'" class="helper-owned-primary" type="button" :disabled="actionLoading" @click="deliver(item)">{{ actionLoading ? "Передаём…" : "Отметить передачу" }}</button>
          <p v-else-if="item.fulfillment_status === 'delivered'">Сертификат передан. Ожидается подтверждение получения заявителем.</p>
          <p v-else>Получение подтверждено заявителем, заявка закрыта.</p>
        </footer>
      </article>
    </div>

    <nav v-if="totalPages > 1" class="helper-owned-pagination" aria-label="Страницы моей помощи"><button type="button" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">←</button><button v-for="page in totalPages" :key="page" type="button" :class="{ active: page === currentPage }" @click="changePage(page)">{{ page }}</button><button type="button" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">→</button></nav>

    <div v-if="selected" class="helper-owned-overlay" role="presentation" @mousedown.self="selected = null">
      <section class="helper-owned-dialog" role="dialog" aria-modal="true" aria-labelledby="helper-certificate-title">
        <button class="helper-owned-dialog__close" type="button" aria-label="Закрыть" @click="selected = null">×</button>
        <h2 id="helper-certificate-title">Создать сертификат</h2><p>{{ selected.title }}</p>
        <label>Поставщик<input v-model="form.provider_name" maxlength="120" placeholder="Название демонстрационного поставщика" /></label>
        <label>Сумма, ₽<input v-model="form.amount" type="number" min="0.01" step="0.01" /></label>
        <p class="helper-owned-dialog__note">Создаётся демонстрационный сертификат без реальной денежной ценности.</p>
        <p v-if="modalError" class="helper-message helper-message--error">{{ modalError }}</p>
        <div><button type="button" @click="selected = null">Отмена</button><button type="button" :disabled="actionLoading" @click="submitCertificate">{{ actionLoading ? "Создаём…" : "Создать" }}</button></div>
      </section>
    </div>
  </section>
</template>
