<script setup>
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authStore } from "../stores/authStore";

const route = useRoute();
const router = useRouter();
const user = authStore.currentUser;
const initial = computed(() => (user.value?.username || "П").charAt(0).toUpperCase());

const menu = [
  { label: "Обзор", to: "/helper/overview", icon: "user.svg", key: "overview" },
  { label: "Заявки на помощь", to: "/helper/requests", icon: "file-text.svg", key: "requests" },
  { label: "Моя помощь", to: "/helper/my-help", icon: "heart-outline.svg", key: "my-help" },
  { label: "Сохранённые", to: "/helper/saved", icon: "bookmark.svg", key: "saved" },
  { label: "Настройки", to: "/helper/settings", icon: "filter.svg", key: "settings" },
];

function isActive(item) {
  return route.path.endsWith(`/${item.key}`);
}

async function signOut() {
  authStore.logout();
  await router.replace("/");
}

onMounted(() => document.body.classList.add("helper-dashboard-open"));
onBeforeUnmount(() => document.body.classList.remove("helper-dashboard-open"));
</script>

<template>
  <div class="helper-shell">
    <header class="helper-header">
      <RouterLink class="helper-brand" to="/">
        <span class="helper-brand__mark"><img src="/icons/logo-heart.svg" alt="" /></span>
        <span>Тихая помощь</span>
      </RouterLink>
    </header>

    <div class="helper-workspace">
      <aside class="helper-sidebar">
        <div class="helper-profile">
          <span class="helper-profile__avatar">{{ initial }}</span>
          <div>
            <strong>{{ user?.username || "Помощник" }}</strong>
            <span>{{ user?.email || "Email не указан" }}</span>
          </div>
        </div>

        <nav class="helper-nav" aria-label="Кабинет помощника">
          <RouterLink
            v-for="item in menu"
            :key="item.key"
            :to="item.to"
            class="helper-nav__item"
            :class="{ 'helper-nav__item--active': isActive(item) }"
          >
            <img :src="`/icons/${item.icon}`" alt="" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>

        <button class="helper-logout" type="button" @click="signOut">
          <img src="/icons/exit.svg" alt="" aria-hidden="true" /> Выйти
        </button>
      </aside>

      <main class="helper-content">
        <RouterView />
      </main>
    </div>
  </div>
</template>
