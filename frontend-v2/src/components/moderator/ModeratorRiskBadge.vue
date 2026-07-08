<script setup>
import { computed } from "vue";
const props = defineProps({ level: { type: String, default: "low" }, action: { type: String, default: "" } });
const tone = computed(() => props.action === "block" || ["high", "critical"].includes(props.level) ? "high" : props.level === "medium" || props.action === "manual_review" ? "medium" : "low");
const label = computed(() => ({ low: "Низкий риск", medium: "Средний риск", high: "Высокий риск" }[tone.value]));
</script>
<template><span :class="`moderator-risk moderator-risk--${tone}`">{{ label }}</span></template>
