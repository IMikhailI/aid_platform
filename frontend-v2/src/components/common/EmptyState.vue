<script setup>
defineProps({ title: { type: String, required: true }, text: { type: String, required: true } });
</script>

<template>
  <section class="empty-state">
    <div class="empty-state__mark" aria-hidden="true">→</div>
    <div><h2>{{ title }}</h2><p>{{ text }}</p></div>
  </section>
</template>
