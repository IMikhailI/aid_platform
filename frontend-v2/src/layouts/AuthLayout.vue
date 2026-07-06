<script setup>
import { onBeforeUnmount, onMounted } from "vue";
import LandingPage from "../pages/public/LandingPage.vue";

defineProps({
  title: { type: String, required: true },
  mode: { type: String, required: true },
});

onMounted(() => document.body.classList.add("auth-modal-open"));
onBeforeUnmount(() => document.body.classList.remove("auth-modal-open"));
</script>

<template>
  <div class="auth-background" inert aria-hidden="true">
    <LandingPage />
  </div>

  <main class="auth-overlay">
    <section class="auth-dialog" :class="`auth-dialog--${mode}`" :aria-labelledby="`${mode}-title`">
      <header class="auth-dialog__header">
        <h1 :id="`${mode}-title`">{{ title }}</h1>
        <RouterLink class="auth-dialog__close" to="/" aria-label="Закрыть">×</RouterLink>
      </header>

      <nav class="auth-tabs" aria-label="Авторизация">
        <RouterLink class="auth-tabs__link" :class="{ 'auth-tabs__link--active': mode === 'login' }" to="/login">
          Вход
        </RouterLink>
        <RouterLink class="auth-tabs__link" :class="{ 'auth-tabs__link--active': mode === 'register' }" to="/register">
          Регистрация
        </RouterLink>
      </nav>

      <div class="auth-dialog__body">
        <slot />
      </div>
    </section>
  </main>
</template>
