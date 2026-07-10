<script setup>
import { useRouter } from "vue-router";
import { authStore } from "../stores/authStore";

defineProps({ title: { type: String, required: true } });
const router = useRouter();

async function signOut() {
  authStore.logout();
  await router.replace("/");
}
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <RouterLink class="app-brand" to="/">Тихая помощь</RouterLink>
      <div class="app-user">
        <span>{{ authStore.currentUser.value?.username }}</span>
        <button class="button button--light" type="button" @click="signOut">Выйти</button>
      </div>
    </header>
    <main class="dashboard">
      <p class="dashboard__eyebrow">Демонстрационный MVP</p>
      <h1>{{ title }}</h1>
      <slot />
    </main>
  </div>
</template>
