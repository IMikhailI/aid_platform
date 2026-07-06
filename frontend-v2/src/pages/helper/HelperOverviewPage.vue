<script setup>
import HelperEmptyState from "../../components/helper/HelperEmptyState.vue";
import { savedRequestIds } from "../../stores/helperSavedStore";
import { authStore } from "../../stores/authStore";
</script>

<template>
  <section class="helper-page">
    <header class="helper-page__heading">
      <h1>Добро пожаловать, {{ authStore.currentUser.value?.username || "помощник" }}!</h1>
      <p>Просматривайте историю оказанной помощи и находите новые запросы</p>
    </header>

    <div class="helper-stats">
      <article><span class="helper-stat-icon helper-stat-icon--purple">♡</span><h2>Оказано помощи</h2><strong>—</strong></article>
      <article><span class="helper-stat-icon helper-stat-icon--blue">◷</span><h2>В процессе</h2><strong>—</strong></article>
      <article>
        <span class="helper-stat-icon helper-stat-icon--yellow"><img src="/icons/bookmark.svg" alt="" /></span>
        <h2>Сохранено</h2>
        <strong>{{ savedRequestIds.length }}</strong>
      </article>
    </div>

    <section class="helper-panel helper-activity">
      <h2>Последняя активность</h2>
      <HelperEmptyState title="История помощи пока недоступна" text="Backend пока не предоставляет список заявок, принятых помощником." />
    </section>
  </section>
</template>
