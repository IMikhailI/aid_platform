<template>
  <section>
    <h2>Login</h2>
    <form @submit.prevent="login" class="card">
      <label>
        Username
        <input v-model="username" required />
      </label>

      <label>
        Password
        <input v-model="password" type="password" required />
      </label>

      <button :disabled="loading">{{ loading ? "Loading..." : "Sign in" }}</button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </section>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import api from "../services/api";
import { setAuth } from "../services/auth";

const router = useRouter();
const username = ref("");
const password = ref("");
const loading = ref(false);
const error = ref("");

async function login() {
  try {
    loading.value = true;
    error.value = "";

    // 1) JWT
    const tokenResp = await api.post("/api/auth/token/", {
      username: username.value,
      password: password.value,
    });

    const access = tokenResp.data.access;
    const refresh = tokenResp.data.refresh;

    // Временно сохраним токены, чтобы пройти /me/
    setAuth({ access, refresh, role: "", username: username.value });

    // 2) Узнаем роль честно с backend
    const meResp = await api.get("/api/auth/me/");
    const me = meResp.data; // {id, username, email, role, region}

    // Обновим auth уже с ролью
    setAuth({
      access,
      refresh,
      role: me.role,
      username: me.username,
    });

    if (me.role === "helper") router.push("/helper");
    else if (me.role === "moderator" || me.role === "admin") router.push("/moderator");
    else router.push("/applicant");
  } catch (e) {
    error.value = e?.response?.data?.detail || "Login failed";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.card {
  max-width: 380px;
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid #ddd;
  border-radius: 10px;
}
label { display: grid; gap: 6px; }
input { padding: 8px; }
.error { color: #b00020; }
</style>

