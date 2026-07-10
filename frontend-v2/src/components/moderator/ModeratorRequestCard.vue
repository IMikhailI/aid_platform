<script setup>
import ModeratorRiskBadge from "./ModeratorRiskBadge.vue";
import { categories, categoryIcons, formatDate, formatMoney, riskLevel, statusLabels, verificationLabels } from "./moderatorView";
defineProps({ request: { type: Object, required: true }, busy: Boolean, actions: { type: Boolean, default: true } });
defineEmits(["details", "approve", "reject"]);
</script>
<template>
  <article class="moderator-request-card">
    <div class="moderator-request-card__body">
      <div class="moderator-request-card__lead">
        <span class="moderator-request-card__icon"><img :src="`/icons/${categoryIcons[request.category] || categoryIcons.other}`" alt="" /></span>
        <div><strong>{{ request.applicant_username }}</strong><span>{{ categories[request.category] || categories.other }}</span><small>⌖ {{ request.region }} · {{ formatDate(request.created_at) }}</small></div>
      </div>
      <ModeratorRiskBadge :level="riskLevel(request)" />
      <h2>{{ request.title }}</h2>
      <div class="moderator-request-card__facts">
        <div><small>Бюджет</small><strong>{{ formatMoney(request.requested_amount) }}</strong></div>
        <span>Срочность: {{ request.urgency }}/5</span>
        <span v-if="!actions" class="moderator-status-mark">{{ statusLabels[request.status] || request.status }}</span>
        <span :class="`moderator-verification moderator-verification--${request.applicant_verification_status}`">Профиль: {{ verificationLabels[request.applicant_verification_status] || request.applicant_verification_status }}</span>
        <span v-if="request.is_flagged" class="moderator-flag">⚑ Требует внимания</span>
      </div>
    </div>
    <footer>
      <button class="moderator-link-button" type="button" @click="$emit('details', request)"><img src="/icons/eye.svg" alt="" /> Подробнее</button>
      <div v-if="actions">
        <button class="moderator-reject-button" type="button" :disabled="busy" @click="$emit('reject', request)"><img src="/icons/x-circle.svg" alt="" /> Отклонить</button>
        <button class="moderator-approve-button" type="button" :disabled="busy" @click="$emit('approve', request)"><img src="/icons/check-circle.svg" alt="" /> Одобрить</button>
      </div>
    </footer>
  </article>
</template>
