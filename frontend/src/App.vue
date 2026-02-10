<template>
  <div class="app">
    <header class="topbar">
      <h1>Aid Platform</h1>
      <div class="right" v-if="auth">
        <span class="meta">user: {{ username }} ({{ role }})</span>
        <button @click="logout">Logout</button>
      </div>
    </header>

    <main class="container">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter } from "vue-router";
import { clearAuth, getRole, getUsername, isAuthenticated } from "./services/auth";

const router = useRouter();
const auth = computed(() => isAuthenticated());
const role = computed(() => getRole());
const username = computed(() => getUsername());

function logout() {
  clearAuth();
  router.push("/login");
}
</script>

<style scoped>
.app { font-family: Arial, sans-serif; color: #111; }
.topbar {
  height: 64px; display: flex; justify-content: space-between; align-items: center;
  padding: 0 16px; border-bottom: 1px solid #ddd;
}
.container { padding: 16px; max-width: 1000px; margin: 0 auto; }
.right { display: flex; align-items: center; gap: 12px; }
.meta { color: #555; font-size: 14px; }
button { padding: 8px 12px; cursor: pointer; }
</style>

