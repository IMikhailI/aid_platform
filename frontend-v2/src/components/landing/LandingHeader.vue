<script setup>
import { useRouter } from "vue-router";

const router = useRouter();

async function openLogin() {
  if (router.currentRoute.value.path !== "/login") {
    await router.push("/login");
  }
}
</script>

<template>
  <header class="header" role="banner">
    <div class="container header__inner">
      <div class="header__brand" aria-label="Логотип платформы Тихая помощь">
        <span class="header__brand-mark" aria-hidden="true">
          <img class="header__brand-icon" src="/icons/logo-heart.svg" alt="" aria-hidden="true" />
        </span>
        <span class="header__brand-text">Тихая помощь</span>
      </div>

      <nav class="header__nav" role="navigation" aria-label="Основная навигация">
        <span class="header__link">О платформе</span>
      </nav>

      <button class="header__button" type="button" aria-label="Войти в личный кабинет" @click="openLogin">
        Войти
      </button>
    </div>
  </header>
</template>
