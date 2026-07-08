<script setup>
import { reactive, ref, watch } from "vue";
const props = defineProps({ request: { type: Object, default: null }, mode: { type: String, default: "reject" }, loading: Boolean, error: { type: String, default: "" } });
const emit = defineEmits(["close", "confirm"]);
const localError = ref("");
const form = reactive({ comment: "", newAction: "manual_review" });
watch(() => props.request?.id, () => { form.comment = ""; form.newAction = "manual_review"; localError.value = ""; });
function submit() {
  localError.value = "";
  if (!form.comment.trim()) { localError.value = "Укажите комментарий к решению"; return; }
  emit("confirm", { comment: form.comment.trim(), newAction: form.newAction });
}
</script>
<template>
  <div v-if="request" class="moderator-overlay" role="presentation" @mousedown.self="emit('close')">
    <section class="moderator-dialog moderator-decision-dialog" role="dialog" aria-modal="true">
      <button class="moderator-dialog__close" type="button" aria-label="Закрыть" @click="emit('close')">×</button>
      <span :class="`moderator-decision-dialog__icon moderator-decision-dialog__icon--${mode}`"><img :src="mode === 'override' ? '/icons/shield.svg' : '/icons/x-circle.svg'" alt="" /></span>
      <h2>{{ mode === "override" ? "Изменить fraud-решение" : "Отклонить заявку" }}</h2>
      <p>{{ request.title }}</p>
      <label v-if="mode === 'override'">Новое действие<select v-model="form.newAction"><option value="manual_review">Ручная проверка</option><option value="allow">Разрешить публикацию</option></select></label>
      <label>{{ mode === "override" ? "Причина override" : "Комментарий заявителю" }}<textarea v-model="form.comment" rows="4" maxlength="1000" placeholder="Опишите основание решения"></textarea></label>
      <p v-if="localError || error" class="moderator-message moderator-message--error">{{ localError || error }}</p>
      <div class="moderator-dialog__actions"><button class="moderator-secondary-button" type="button" :disabled="loading" @click="emit('close')">Отмена</button><button :class="mode === 'override' ? 'moderator-primary-button' : 'moderator-danger-button'" type="button" :disabled="loading" @click="submit">{{ loading ? "Сохраняем…" : mode === "override" ? "Применить override" : "Отклонить" }}</button></div>
    </section>
  </div>
</template>
