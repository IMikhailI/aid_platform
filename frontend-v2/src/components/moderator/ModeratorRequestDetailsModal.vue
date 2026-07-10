<script setup>
import { computed, ref, watch } from "vue";
import { getFraudChecks, getFraudDecision, getModeratorApiError, getRequestHistory, recheckFraud } from "../../services/moderatorApi";
import ModeratorRiskBadge from "./ModeratorRiskBadge.vue";
import { categories, formatDate, formatMoney, fraudActions, riskLevel, verificationLabels } from "./moderatorView";

const props = defineProps({ request: { type: Object, default: null }, actionLoading: Boolean });
const emit = defineEmits(["close", "approve", "reject", "override"]);
const loading = ref(false);
const rechecking = ref(false);
const decision = ref(null);
const checks = ref([]);
const history = ref([]);
const error = ref("");

const reasons = computed(() => {
  const value = decision.value?.reasons;
  const list = Array.isArray(value) ? value : value && typeof value === "object" ? Object.values(value) : value ? [value] : [];
  return list.filter((item) => typeof item === "string" && !/(device|user.?agent|ip|hash)/i.test(item));
});

async function loadDetails(id) {
  loading.value = true; error.value = ""; decision.value = null; checks.value = []; history.value = [];
  const [fraudResult, checksResult, historyResult] = await Promise.allSettled([getFraudDecision(id), getFraudChecks(id), getRequestHistory(id)]);
  if (fraudResult.status === "fulfilled") decision.value = fraudResult.value;
  if (checksResult.status === "fulfilled") checks.value = checksResult.value.results;
  if (historyResult.status === "fulfilled") history.value = historyResult.value;
  if (fraudResult.status === "rejected") error.value = "Антифрод-решение пока недоступно. Можно выполнить повторную проверку.";
  loading.value = false;
}

async function recheck() {
  if (!props.request) return;
  rechecking.value = true; error.value = "";
  try {
    const result = await recheckFraud(props.request.id);
    if (result?.detail && !result?.risk_level) error.value = result.detail;
    else decision.value = result;
    const updated = await getFraudChecks(props.request.id);
    checks.value = updated.results;
  } catch (requestError) { error.value = getModeratorApiError(requestError, "Не удалось повторить проверку"); }
  finally { rechecking.value = false; }
}

watch(() => props.request?.id, (id) => { if (id) loadDetails(id); }, { immediate: true });
</script>

<template>
  <div v-if="request" class="moderator-overlay" role="presentation" @mousedown.self="emit('close')">
    <section class="moderator-dialog moderator-details" role="dialog" aria-modal="true" aria-labelledby="moderator-details-title">
      <button class="moderator-dialog__close" type="button" aria-label="Закрыть" @click="emit('close')">×</button>
      <header><span>Заявка #{{ request.id }}</span><h2 id="moderator-details-title">{{ request.title }}</h2><p>{{ categories[request.category] }} · {{ request.region }} · {{ formatDate(request.created_at) }}</p></header>
      <div class="moderator-details__grid">
        <div><span>Заявитель</span><strong>{{ request.applicant_username }}</strong></div>
        <div><span>Верификация</span><strong>{{ verificationLabels[request.applicant_verification_status] }}</strong></div>
        <div><span>Бюджет</span><strong>{{ formatMoney(request.requested_amount) }}</strong></div>
        <div><span>Срочность</span><strong>{{ request.urgency }} из 5</strong></div>
      </div>
      <p class="moderator-details__note">Подробное описание не входит в текущий moderator serializer.</p>

      <section class="moderator-fraud-panel">
        <div class="moderator-fraud-panel__heading"><div><h3>Антифрод-проверка</h3><p>Решение и сигналы автоматической проверки</p></div><button class="moderator-secondary-button" type="button" :disabled="rechecking" @click="recheck">{{ rechecking ? "Проверяем…" : "Проверить снова" }}</button></div>
        <div v-if="loading" class="moderator-inline-loading">Загрузка служебных данных…</div>
        <template v-else>
          <div v-if="decision" class="moderator-fraud-decision">
            <ModeratorRiskBadge :level="riskLevel(request, decision)" :action="decision.action" />
            <div><span>Баллы риска</span><strong>{{ decision.score }}</strong></div>
            <div><span>Базовое действие</span><strong>{{ fraudActions[decision.base_action] || decision.base_action }}</strong></div>
            <div><span>Текущее действие</span><strong>{{ fraudActions[decision.action] || decision.action }}</strong></div>
            <span v-if="decision.is_overridden" class="moderator-override-mark">Override применён</span>
          </div>
          <ul v-if="reasons.length" class="moderator-reasons"><li v-for="reason in reasons" :key="reason">{{ reason }}</li></ul>
          <div v-if="checks.length" class="moderator-checks"><div v-for="check in checks" :key="check.id"><span>{{ check.signal_code }}</span><strong>{{ check.weight > 0 ? "+" : "" }}{{ check.weight }}</strong></div></div>
          <p v-else-if="decision" class="moderator-muted">Дополнительные сигналы отсутствуют.</p>
          <p v-if="decision?.action === 'block'" class="moderator-message moderator-message--warning">Публикация запрещена антифрод-политикой. Выполните override или отклоните заявку.</p>
          <button v-if="decision && ['block', 'manual_review'].includes(decision.action)" class="moderator-override-button" type="button" @click="emit('override', request)">Изменить fraud-действие</button>
        </template>
        <p v-if="error" class="moderator-message moderator-message--warning">{{ error }}</p>
      </section>

      <section v-if="history.length" class="moderator-history"><h3>История статусов</h3><div v-for="item in history" :key="item.id"><span>{{ item.from_status }} → {{ item.to_status }}</span><time>{{ formatDate(item.changed_at) }}</time></div></section>
      <div class="moderator-dialog__actions"><button class="moderator-danger-button" type="button" :disabled="actionLoading" @click="emit('reject', request)">Отклонить</button><button class="moderator-approve-button" type="button" :disabled="actionLoading || decision?.action === 'block'" @click="emit('approve', request)">Одобрить</button></div>
    </section>
  </div>
</template>
