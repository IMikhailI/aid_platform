<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import ApplicantRequestRow from "../../components/applicant/ApplicantRequestRow.vue";
import { confirmApplicantReceipt, getApplicantApiError, getApplicantFulfillment, getApplicantRequests } from "../../services/applicantApi";
import { formatDate, formatMoney } from "../../components/applicant/applicantView";

const requests = ref([]);
const loading = ref(true);
const error = ref("");
const notice = ref("");
const fulfillment = reactive({});
const fulfillmentError = reactive({});
const busy = reactive({});
const historyRequests = computed(() => requests.value.filter((item) => ["in_progress", "closed"].includes(item.status)));
const completed = computed(() => requests.value.filter((item) => item.status === "closed"));
const total = computed(() => completed.value.reduce((sum, item) => sum + Number(item.requested_amount || 0), 0));
const inProgressCount = computed(() => requests.value.filter((item) => item.status === "in_progress").length);

async function loadFulfillment(request, { silent = false } = {}) {
  busy[request.id] = true;
  if (!silent) fulfillmentError[request.id] = "";
  try { fulfillment[request.id] = await getApplicantFulfillment(request.id); }
  catch (requestError) {
    fulfillment[request.id] = null;
    if (!silent) fulfillmentError[request.id] = getApplicantApiError(requestError, "Информация о помощи пока недоступна");
  }
  finally { busy[request.id] = false; }
}

async function confirm(request) {
  busy[request.id] = true;
  fulfillmentError[request.id] = "";
  notice.value = "";
  try {
    await confirmApplicantReceipt(request.id);
    await loadFulfillment(request);
    request.status = "closed";
    notice.value = "Получение помощи подтверждено, заявка закрыта";
  } catch (requestError) {
    fulfillmentError[request.id] = getApplicantApiError(requestError, "Не удалось подтвердить получение");
    busy[request.id] = false;
  }
}

onMounted(async () => {
  try {
    requests.value = await getApplicantRequests();
    await Promise.allSettled(
      requests.value
        .filter((item) => item.status === "in_progress")
        .map((item) => loadFulfillment(item, { silent: true })),
    );
  }
  catch (requestError) { error.value = getApplicantApiError(requestError, "Не удалось загрузить историю"); }
  finally { loading.value = false; }
});
</script>

<template>
  <section class="applicant-page">
    <header class="applicant-page__header"><div><h1>История полученной помощи</h1><p>Завершённые заявки и информация о передаче помощи</p></div></header>
    <p v-if="notice" class="applicant-alert applicant-alert--success">{{ notice }}</p>
    <p v-if="error" class="applicant-alert applicant-alert--error">{{ error }}</p>
    <article class="applicant-history-summary">
      <div><strong>{{ loading ? "—" : completed.length }}</strong><span>Завершено заявок</span></div>
      <div><strong>{{ loading ? "—" : formatMoney(total) }}</strong><span>Сумма завершённых заявок</span></div>
      <div><strong>{{ loading ? "—" : inProgressCount }}</strong><span>Заявок в работе</span></div>
    </article>

    <div class="applicant-list-card" :aria-busy="loading">
      <div v-if="loading" class="applicant-empty"><span class="applicant-spinner"></span><h2>Загружаем историю</h2></div>
      <div v-else-if="!historyRequests.length" class="applicant-empty"><span><img src="/icons/heart-outline.svg" alt="" /></span><h2>История пока пуста</h2><p>Завершённые заявки и переданная помощь появятся здесь.</p></div>
      <ApplicantRequestRow v-for="request in historyRequests" v-else :key="request.id" :request="request" :action-label="fulfillment[request.id] ? '' : 'Информация о помощи'" :busy="busy[request.id]" @action="loadFulfillment(request)">
        <p v-if="fulfillmentError[request.id]" class="applicant-inline-error">{{ fulfillmentError[request.id] }}</p>
        <div v-if="fulfillment[request.id]" class="applicant-fulfillment">
          <div><span>Статус передачи</span><strong>{{ { created: "Подготавливается", delivered: "Передана", confirmed: "Получение подтверждено" }[fulfillment[request.id].status] || fulfillment[request.id].status }}</strong></div>
          <div><span>Поставщик</span><strong>{{ fulfillment[request.id].provider_name }}</strong></div>
          <div><span>Сумма</span><strong>{{ formatMoney(fulfillment[request.id].amount) }}</strong></div>
          <div v-if="fulfillment[request.id].delivered_at"><span>Передано</span><strong>{{ formatDate(fulfillment[request.id].delivered_at) }}</strong></div>
          <div v-if="['delivered', 'confirmed'].includes(fulfillment[request.id].status) && fulfillment[request.id].certificate_code" class="applicant-fulfillment__code"><span>Код сертификата</span><code>{{ fulfillment[request.id].certificate_code }}</code></div>
          <button v-if="fulfillment[request.id].status === 'delivered'" class="applicant-button" type="button" :disabled="busy[request.id]" @click="confirm(request)">{{ busy[request.id] ? "Подтверждаем…" : "Подтвердить получение" }}</button>
        </div>
      </ApplicantRequestRow>
    </div>
  </section>
</template>
