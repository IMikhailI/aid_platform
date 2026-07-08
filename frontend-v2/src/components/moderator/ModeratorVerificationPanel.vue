<script setup>
import { ref } from "vue";
import { decideVerification, getModeratorApiError } from "../../services/moderatorApi";
import { formatDate } from "./moderatorView";

const props = defineProps({ items: { type: Array, default: () => [] }, loading: Boolean });
const emit = defineEmits(["decided"]);
const busyId = ref(null);
const error = ref("");

async function decide(item, decision) {
  const comment = decision === "verified" ? "Профиль проверен модератором" : "Данные профиля требуют уточнения";
  busyId.value = item.id; error.value = "";
  try { await decideVerification(item.id, decision, comment); emit("decided", item.id); }
  catch (requestError) { error.value = getModeratorApiError(requestError, "Не удалось обработать верификацию"); }
  finally { busyId.value = null; }
}
</script>
<template>
  <section class="moderator-verification-panel">
    <header><div><h2>Верификация профилей</h2><p>Компактная очередь заявителей, ожидающих проверки</p></div><span>{{ items.length }}</span></header>
    <p v-if="error" class="moderator-message moderator-message--error">{{ error }}</p>
    <div v-if="loading" class="moderator-inline-loading">Загрузка верификаций…</div>
    <div v-else-if="!items.length" class="moderator-verification-panel__empty">Нет профилей, ожидающих проверки.</div>
    <article v-for="item in items.slice(0, 5)" v-else :key="item.id">
      <div><strong>{{ item.applicant_username }}</strong><span>{{ item.region }} · {{ formatDate(item.submitted_at) }}</span><small>Семья: {{ item.household_size }}, иждивенцев: {{ item.dependents_count }}</small></div>
      <div><button type="button" :disabled="busyId === item.id" @click="decide(item, 'rejected')">Отклонить</button><button type="button" :disabled="busyId === item.id" @click="decide(item, 'verified')">Подтвердить</button></div>
    </article>
  </section>
</template>
