<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import AuthLayout from "../../layouts/AuthLayout.vue";
import { getApiError } from "../../services/errors";
import { authStore } from "../../stores/authStore";

const username = ref("");
const password = ref("");
const remember = ref(false);
const errorMessage = ref("");
const route = useRoute();
const registrationComplete = computed(() => route.query.registered === "1");

async function submit() {
  errorMessage.value = "";

  try {
    const user = await authStore.login(username.value, password.value);
    const rolePath = authStore.redirectByRole(user.role);
    const requestedPath = typeof route.query.redirect === "string" ? route.query.redirect : "";
    const isAllowedRedirect = requestedPath === rolePath || requestedPath.startsWith(`${rolePath}/`);
    window.location.assign(isAllowedRedirect ? requestedPath : rolePath);
  } catch (error) {
    errorMessage.value = error.response?.status === 401
      ? "Неверное имя пользователя или пароль."
      : getApiError(error, "Не удалось войти. Проверьте соединение и попробуйте снова.");
  }
}
</script>

<template>
  <AuthLayout title="Вход в аккаунт" mode="login">
    <p v-if="registrationComplete" class="auth-notice auth-notice--success" role="status">
      Регистрация выполнена, войдите в систему
    </p>

    <form class="auth-form" @submit.prevent="submit">
      <label class="auth-field">
        <span class="auth-field__label">Имя пользователя</span>
        <span class="auth-field__control">
          <img src="/icons/user.svg" alt="" aria-hidden="true" />
          <input v-model.trim="username" name="username" autocomplete="username" placeholder="Ваш логин" required />
        </span>
      </label>

      <label class="auth-field">
        <span class="auth-field__label">Пароль</span>
        <span class="auth-field__control">
          <img src="/icons/lock.svg" alt="" aria-hidden="true" />
          <input v-model="password" name="password" type="password" autocomplete="current-password" placeholder="••••••••" required />
        </span>
      </label>

      <div class="auth-form__options">
        <label class="auth-checkbox"><input v-model="remember" type="checkbox" /> <span>Запомнить меня</span></label>
        <button class="auth-form__link" type="button">Забыли пароль?</button>
      </div>

      <p v-if="errorMessage" class="auth-notice auth-notice--error" role="alert">{{ errorMessage }}</p>

      <button class="auth-submit" type="submit" :disabled="authStore.state.loading">
        {{ authStore.state.loading ? "Входим…" : "Войти" }}
      </button>

      <div class="auth-divider"><span>или</span></div>
      <button class="auth-provider" type="button" disabled title="Интеграция недоступна">
        Госуслуги
      </button>
    </form>
  </AuthLayout>
</template>
