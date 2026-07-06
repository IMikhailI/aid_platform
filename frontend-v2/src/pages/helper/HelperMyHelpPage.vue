<script setup>
import HelperEmptyState from "../../components/helper/HelperEmptyState.vue";

// TODO: Replace this empty state when backend exposes a helper-owned requests list endpoint.
</script>

<template>
  <section class="helper-page">
    <header class="helper-page__heading">
      <h1>Моя помощь</h1>
      <p>История оказанной помощи и активные отклики</p>
    </header>

    <div class="helper-summary-cards">
      <article><span>Всего оказано помощи</span><strong>—</strong></article>
      <article><span>Количество запросов</span><strong>—</strong></article>
      <article><span>Людей помогли</span><strong>—</strong></article>
    </div>

    <HelperEmptyState title="Здесь появится ваша помощь" text="Для списка активных и завершённых откликов пока нет backend endpoint." />
  </section>
</template>
