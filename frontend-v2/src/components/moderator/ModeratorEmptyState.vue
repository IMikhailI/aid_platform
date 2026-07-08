<script setup>
defineProps({ title: { type: String, required: true }, text: { type: String, required: true }, icon: { type: String, default: "check-circle.svg" } });
</script>
<template><div class="moderator-empty"><span><img :src="`/icons/${icon}`" alt="" /></span><h2>{{ title }}</h2><p>{{ text }}</p></div></template>
