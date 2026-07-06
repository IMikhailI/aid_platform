<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import AuthLayout from "../../layouts/AuthLayout.vue";
import { getApiError } from "../../services/errors";
import { authStore } from "../../stores/authStore";

const router = useRouter();
const errorMessage = ref("");
const form = reactive({
  username: "",
  region: "",
  email: "",
  password: "",
  passwordConfirmation: "",
  role: "helper",
  termsAccepted: false,
  privacyAccepted: false,
});

async function submit() {
  errorMessage.value = "";

  if (form.password !== form.passwordConfirmation) {
    errorMessage.value = "Пароли не совпадают.";
    return;
  }

  if (!form.termsAccepted || !form.privacyAccepted) {
    errorMessage.value = "Подтвердите условия использования и политику конфиденциальности.";
    return;
  }

  try {
    await authStore.register({
      username: form.username,
      email: form.email,
      password: form.password,
      role: form.role,
      region: form.region,
    });
    await router.push({ path: "/login", query: { registered: "1" } });
  } catch (error) {
    errorMessage.value = getApiError(error, "Не удалось зарегистрироваться. Попробуйте снова.");
  }
}
</script>

<template>
  <AuthLayout title="Регистрация" mode="register">
    <form class="auth-form auth-form--register" @submit.prevent="submit">
      <label class="auth-field">
        <span class="auth-field__label">Имя пользователя</span>
        <span class="auth-field__control">
          <img src="/icons/user.svg" alt="" aria-hidden="true" />
          <input v-model.trim="form.username" name="username" autocomplete="username" placeholder="Ваш логин" maxlength="150" required />
        </span>
      </label>

      <label class="auth-field">
        <span class="auth-field__label">Регион</span>
        <span class="auth-field__control">
          <img src="/icons/map-pin.svg" alt="" aria-hidden="true" />
          <input v-model.trim="form.region" name="region" autocomplete="address-level1" placeholder="Ваш регион" maxlength="120" />
        </span>
      </label>

      <fieldset class="auth-role">
        <legend>Я хочу</legend>
        <div class="auth-role__options">
          <label class="auth-role-card" :class="{ 'auth-role-card--active': form.role === 'helper' }">
            <input v-model="form.role" type="radio" name="role" value="helper" />
            <img src="/icons/heart-outline.svg" alt="" aria-hidden="true" />
            <span>Помогать другим</span>
          </label>
          <label class="auth-role-card" :class="{ 'auth-role-card--active': form.role === 'applicant' }">
            <input v-model="form.role" type="radio" name="role" value="applicant" />
            <img src="/icons/logo-heart.svg" alt="" aria-hidden="true" />
            <span>Получить помощь</span>
          </label>
        </div>
      </fieldset>

      <label class="auth-field">
        <span class="auth-field__label">Email</span>
        <span class="auth-field__control">
          <img src="/icons/mail.svg" alt="" aria-hidden="true" />
          <input v-model.trim="form.email" name="email" type="email" autocomplete="email" placeholder="your@email.com" maxlength="254" />
        </span>
      </label>

      <label class="auth-field">
        <span class="auth-field__label">Пароль</span>
        <span class="auth-field__control">
          <img src="/icons/lock.svg" alt="" aria-hidden="true" />
          <input v-model="form.password" name="password" type="password" autocomplete="new-password" placeholder="••••••••" minlength="8" required />
        </span>
      </label>

      <label class="auth-field">
        <span class="auth-field__label">Пароль</span>
        <span class="auth-field__control">
          <img src="/icons/lock.svg" alt="" aria-hidden="true" />
          <input v-model="form.passwordConfirmation" name="password_confirmation" type="password" autocomplete="new-password" placeholder="••••••••" minlength="8" required />
        </span>
      </label>

      <div class="auth-consent">
        <p>Регистрируясь, вы соглашаетесь с</p>
        <label class="auth-checkbox"><input v-model="form.termsAccepted" type="checkbox" /> <span>Условиями использования</span></label>
        <label class="auth-checkbox"><input v-model="form.privacyAccepted" type="checkbox" /> <span>Политикой конфиденциальности</span></label>
      </div>

      <p v-if="errorMessage" class="auth-notice auth-notice--error" role="alert">{{ errorMessage }}</p>

      <button class="auth-submit" type="submit" :disabled="authStore.state.loading">
        {{ authStore.state.loading ? "Регистрируем…" : "Зарегистрироваться" }}
      </button>
    </form>
  </AuthLayout>
</template>
