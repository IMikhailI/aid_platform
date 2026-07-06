<script setup>
import { categoryLabels, formatDate, formatMoney, requestStatus } from "./applicantView";
defineProps({ request: { type: Object, required: true }, actionLabel: { type: String, default: "" }, busy: Boolean });
defineEmits(["action"]);
</script>

<template>
  <article class="applicant-request-row">
    <span class="applicant-request-row__icon"><img src="/icons/package-box.svg" alt="" /></span>
    <div class="applicant-request-row__body">
      <div class="applicant-request-row__top">
        <div><h3>{{ request.title }}</h3><p>{{ categoryLabels[request.category] || request.category }} · {{ formatDate(request.created_at) }} · {{ request.region }}</p></div>
        <div class="applicant-request-row__meta">
          <span :class="`applicant-pill applicant-pill--${(requestStatus[request.status] || requestStatus.draft)[1]}`">{{ (requestStatus[request.status] || [request.status])[0] }}</span>
          <strong>{{ formatMoney(request.requested_amount) }}</strong>
        </div>
      </div>
      <p class="applicant-request-row__description">{{ request.description }}</p>
      <div v-if="actionLabel" class="applicant-request-row__actions">
        <button class="applicant-text-button" type="button" :disabled="busy" @click="$emit('action')">{{ busy ? "Загрузка…" : actionLabel }}</button>
      </div>
      <slot />
    </div>
  </article>
</template>
