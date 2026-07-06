<script setup>
import LandingHeader from "../components/landing/LandingHeader.vue";
import LandingFooter from "../components/landing/LandingFooter.vue";
</script>

<template>
  <LandingHeader />
  <main class="main" role="main" aria-label="Основной контент сайта"><slot /></main>
  <LandingFooter />
</template>
