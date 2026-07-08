<script setup>
defineProps({ pending: { type: [Number, String], default: "—" }, approved: { type: [Number, String], default: "—" }, rejected: { type: [Number, String], default: "—" } });
const tabs = [
  { label: "На модерации", to: "/moderator/pending", icon: "clock.svg", key: "pending" },
  { label: "Одобренные", to: "/moderator/approved", icon: "check-circle.svg", key: "approved" },
  { label: "Отклонённые", to: "/moderator/rejected", icon: "x-circle.svg", key: "rejected" },
];
</script>
<template>
  <nav class="moderator-tabs" aria-label="Статусы модерации">
    <RouterLink v-for="tab in tabs" :key="tab.key" :to="tab.to">
      <img :src="`/icons/${tab.icon}`" alt="" />{{ tab.label }}<span>{{ $props[tab.key] }}</span>
    </RouterLink>
  </nav>
</template>
