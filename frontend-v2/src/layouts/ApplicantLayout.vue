<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { authStore } from "../stores/authStore";
import { getApplicantProfile } from "../services/applicantApi";

const route = useRoute();
const router = useRouter();
const profile = ref(null);
const user = authStore.currentUser;

const initial = computed(() => (user.value?.username || "П").charAt(0).toUpperCase());
const verification = computed(() => {
  const status = profile.value?.verification_status;
  if (status === "verified") return { text: "Профиль проверен", tone: "verified" };
  if (status === "pending") return { text: "Проверка профиля", tone: "pending" };
  if (status === "rejected") return { text: "Нужны уточнения", tone: "rejected" };
  return { text: "Профиль не проверен", tone: "neutral" };
});

const menu = [
  { label: "Обзор", to: "/applicant/overview", icon: "user.svg", key: "overview" },
  { label: "Мои заявки", to: "/applicant/requests", icon: "file-text.svg", key: "requests" },
  { label: "История помощи", to: "/applicant/history", icon: "heart-outline.svg", key: "history" },
  { label: "Настройки", to: "/applicant/settings", icon: "filter.svg", key: "settings" },
];

function isActive(item) {
  return route.path.endsWith(`/${item.key}`);
}

async function signOut() {
  authStore.logout();
  await router.replace("/");
}

onMounted(async () => {
  document.body.classList.add("applicant-dashboard-open");
  try {
    profile.value = await getApplicantProfile();
  } catch {
    profile.value = null;
  }
});
onBeforeUnmount(() => document.body.classList.remove("applicant-dashboard-open"));
</script>

<template>
  <div class="applicant-shell">
    <header class="applicant-header">
      <RouterLink class="applicant-brand" to="/">
        <span class="applicant-brand__mark"><img src="/icons/logo-heart.svg" alt="" /></span>
        <span>Тихая помощь</span>
      </RouterLink>
    </header>

    <div class="applicant-workspace">
      <aside class="applicant-sidebar">
        <div class="applicant-profile">
          <span class="applicant-profile__avatar">{{ initial }}</span>
          <div class="applicant-profile__copy">
            <strong>{{ user?.username || "Получатель помощи" }}</strong>
            <span>Получатель помощи</span>
            <small :class="`applicant-profile__status--${verification.tone}`">
              <i aria-hidden="true"></i>{{ verification.text }}
            </small>
          </div>
        </div>

        <nav class="applicant-nav" aria-label="Кабинет получателя помощи">
          <RouterLink
            v-for="item in menu"
            :key="item.key"
            :to="item.to"
            class="applicant-nav__item"
            :class="{ 'applicant-nav__item--active': isActive(item) }"
          >
            <img :src="`/icons/${item.icon}`" alt="" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </nav>

        <button class="applicant-logout" type="button" @click="signOut">
          <img src="/icons/exit.svg" alt="" aria-hidden="true" /> Выйти
        </button>
      </aside>

      <main class="applicant-content"><RouterView /></main>
    </div>
  </div>
</template>
