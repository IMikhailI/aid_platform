<script setup>
defineProps({
  title: { type: String, required: true },
  text: { type: String, required: true },
});
</script>

<template>
  <div class="helper-empty">
    <span class="helper-empty__icon" aria-hidden="true">♡</span>
    <div>
      <h2>{{ title }}</h2>
      <p>{{ text }}</p>
    </div>
  </div>
</template>
