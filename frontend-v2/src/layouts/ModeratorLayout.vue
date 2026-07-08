<script setup>
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import { authStore } from "../stores/authStore";

const router = useRouter();
const user = authStore.currentUser;
const roleLabel = computed(() => user.value?.role === "admin" ? "Администратор" : "Модератор");

function logout() {
  authStore.logout();
  router.push("/");
}

onMounted(() => document.body.classList.add("moderator-dashboard-open"));
onBeforeUnmount(() => document.body.classList.remove("moderator-dashboard-open"));
</script>

<template>
  <div class="moderator-shell">
    <header class="moderator-header">
      <RouterLink class="moderator-brand" to="/moderator/pending">
        <span><img src="/icons/shield.svg" alt="" /></span>
        <strong>Панель модерации</strong>
      </RouterLink>
      <div class="moderator-account">
        <div><strong>{{ user?.username || roleLabel }}</strong><span>{{ roleLabel }}</span></div>
        <button type="button" @click="logout"><img src="/icons/exit.svg" alt="" /> Выйти</button>
      </div>
    </header>
    <main class="moderator-main"><RouterView /></main>
  </div>
</template>
