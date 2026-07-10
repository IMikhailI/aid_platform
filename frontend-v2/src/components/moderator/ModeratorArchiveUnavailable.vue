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
    <div class="moderator-kpis"><article><span><img src="/icons/clock.svg" alt="" /></span><div><strong>{{ pending }}</strong><b>На модерации</b><small>Основной demo-flow</small></div></article><article><span><img src="/icons/check-circle.svg" alt="" /></span><div><strong>—</strong><b>Одобрено</b><small>Будущий read-only архив</small></div></article><article><span><img src="/icons/x-circle.svg" alt="" /></span><div><strong>—</strong><b>Отклонено</b><small>Будущий read-only архив</small></div></article><article><span><img src="/icons/trending-up.svg" alt="" /></span><div><strong>—</strong><b>Процент одобрения</b><small>После endpoint истории</small></div></article></div>
    <section class="moderator-queue-toolbar"><ModeratorStatusTabs :pending="pending" /><div class="moderator-archive-search"><img src="/icons/search.svg" alt="" /><span>История решений будет добавлена отдельным read-only endpoint</span></div></section>
    <ModeratorEmptyState :title="isApproved ? 'История одобренных заявок будет добавлена отдельным read-only endpoint' : 'История отклонённых заявок будет добавлена отдельным read-only endpoint'" text="В текущем MVP основной демонстрационный сценарий проходит через вкладку «На модерации»." :icon="isApproved ? 'check-circle.svg' : 'x-circle.svg'" />
  </section>
</template>
