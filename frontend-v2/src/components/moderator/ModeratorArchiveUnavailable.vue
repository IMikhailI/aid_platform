<script setup>
import { onMounted, ref } from "vue";
import { getModerationQueue } from "../../services/moderatorApi";
import ModeratorEmptyState from "./ModeratorEmptyState.vue";
import ModeratorStatusTabs from "./ModeratorStatusTabs.vue";
const props = defineProps({ status: { type: String, required: true } });
const pending = ref("—");
const isApproved = props.status === "approved";
onMounted(async () => { try { pending.value = (await getModerationQueue({ page_size: 1 })).count; } catch { pending.value = "—"; } });
</script>
<template>
  <section class="moderator-page">
    <div class="moderator-kpis"><article><span><img src="/icons/clock.svg" alt="" /></span><div><strong>{{ pending }}</strong><b>На модерации</b><small>Требуют проверки</small></div></article><article><span><img src="/icons/check-circle.svg" alt="" /></span><div><strong>—</strong><b>Одобрено</b><small>История недоступна в API</small></div></article><article><span><img src="/icons/x-circle.svg" alt="" /></span><div><strong>—</strong><b>Отклонено</b><small>История недоступна в API</small></div></article><article><span><img src="/icons/trending-up.svg" alt="" /></span><div><strong>—</strong><b>Процент одобрения</b><small>Нет серверной статистики</small></div></article></div>
    <section class="moderator-queue-toolbar"><ModeratorStatusTabs :pending="pending" /><div class="moderator-archive-search"><img src="/icons/search.svg" alt="" /><span>Поиск по архиву станет доступен вместе с API истории</span></div></section>
    <ModeratorEmptyState :title="isApproved ? 'История одобренных заявок недоступна' : 'История отклонённых заявок недоступна'" text="Текущий backend endpoint возвращает только заявки со статусом «На модерации». Для этого раздела нужен отдельный read-only endpoint истории." :icon="isApproved ? 'check-circle.svg' : 'x-circle.svg'" />
  </section>
</template>
