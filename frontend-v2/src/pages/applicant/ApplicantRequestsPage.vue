<script setup>
import { onMounted, reactive, ref } from "vue";
import { authStore } from "../../stores/authStore";
import {
  confirmApplicantReceipt,
  getApplicantApiError,
  getApplicantFulfillment,
  getApplicantRequests,
} from "../../services/applicantApi";
import ApplicantCreateRequestModal from "../../components/applicant/ApplicantCreateRequestModal.vue";
import ApplicantRequestRow from "../../components/applicant/ApplicantRequestRow.vue";

const requests = ref([]);
const loading = ref(true);
const error = ref("");
const notice = ref("");
const showCreate = ref(false);
const fulfillment = reactive({});
const fulfillmentError = reactive({});
const busy = reactive({});

async function loadFulfillment(request, { silent = false } = {}) {
  if (request.status !== "in_progress") return;
  busy[request.id] = true;
  if (!silent) fulfillmentError[request.id] = "";
  try {
    fulfillment[request.id] = await getApplicantFulfillment(request.id);
  } catch (requestError) {
    fulfillment[request.id] = null;
    if (!silent) fulfillmentError[request.id] = getApplicantApiError(requestError, "Информация о помощи пока недоступна");
  } finally {
    busy[request.id] = false;
  }
}

async function loadRequests() {
  loading.value = true;
  error.value = "";
  try {
    requests.value = await getApplicantRequests();
    await Promise.allSettled(requests.value.filter((item) => item.status === "in_progress").map((item) => loadFulfillment(item, { silent: true })));
  }
  catch (requestError) { error.value = getApplicantApiError(requestError, "Не удалось загрузить заявки"); }
  finally { loading.value = false; }
}

async function created() {
  showCreate.value = false;
  notice.value = "Заявка создана и отправлена на модерацию";
  await loadRequests();
}

async function confirm(request) {
  busy[request.id] = true;
  fulfillmentError[request.id] = "";
  notice.value = "";
  try {
    await confirmApplicantReceipt(request.id);
    await loadRequests();
    notice.value = "Получение помощи подтверждено, заявка закрыта";
  } catch (requestError) {
    fulfillmentError[request.id] = getApplicantApiError(requestError, "Не удалось подтвердить получение");
  } finally {
    busy[request.id] = false;
  }
}

onMounted(loadRequests);
</script>

<template>
  <section class="applicant-page">
    <header class="applicant-page__header">
      <div><h1>Мои заявки</h1><p>Создавайте заявки и отслеживайте их текущий статус</p></div>
      <button class="applicant-button" type="button" @click="showCreate = true">+ Новая заявка</button>
    </header>
    <p v-if="notice" class="applicant-alert applicant-alert--success">{{ notice }}</p>
    <p v-if="error" class="applicant-alert applicant-alert--error">{{ error }}</p>

    <div class="applicant-list-card" :aria-busy="loading">
      <div v-if="loading" class="applicant-empty"><span class="applicant-spinner"></span><h2>Загружаем заявки</h2></div>
      <div v-else-if="!requests.length" class="applicant-empty">
        <span><img src="/icons/file-text.svg" alt="" /></span><h2>У вас пока нет заявок</h2><p>Создайте первую заявку, чтобы запросить необходимую помощь.</p>
        <button class="applicant-button" type="button" @click="showCreate = true">Создать заявку</button>
      </div>
      <ApplicantRequestRow v-for="request in requests" v-else :key="request.id" :request="request">
        <p v-if="fulfillmentError[request.id]" class="applicant-inline-error">{{ fulfillmentError[request.id] }}</p>
        <div v-if="fulfillment[request.id]?.status === 'delivered'" class="applicant-request-row__actions">
          <button class="applicant-button" type="button" :disabled="busy[request.id]" @click="confirm(request)">
            {{ busy[request.id] ? "Подтверждаем…" : "Подтвердить получение" }}
          </button>
        </div>
      </ApplicantRequestRow>
    </div>
    <ApplicantCreateRequestModal v-if="showCreate" :region="authStore.currentUser.value?.region || ''" @close="showCreate = false" @created="created" />
  </section>
</template>
