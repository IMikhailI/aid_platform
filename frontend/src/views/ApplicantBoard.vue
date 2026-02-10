<template>
  <section>
    <h2>Applicant board</h2>

    <form class="card" @submit.prevent="createRequest">
      <h3>Create request</h3>

      <label>Category
        <select v-model="form.category" required>
          <option value="food">food</option>
          <option value="children">children</option>
          <option value="medicine">medicine</option>
          <option value="clothes">clothes</option>
          <option value="other">other</option>
        </select>
      </label>

      <label>Title <input v-model="form.title" required /></label>
      <label>Description <textarea v-model="form.description" required /></label>
      <label>Region <input v-model="form.region" required /></label>
      <label>Amount <input v-model="form.requested_amount" type="number" min="1" required /></label>
      <label>Urgency (1..5) <input v-model.number="form.urgency" type="number" min="1" max="5" required /></label>

      <button>Create</button>
    </form>

    <h3 style="margin-top: 16px;">My requests</h3>
    <button @click="loadMine">Refresh</button>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="list">
      <article class="card" v-for="r in myRequests" :key="r.id">
        <h4>#{{ r.id }} — {{ r.title }}</h4>
        <p>{{ r.category }} | {{ r.region }}</p>
        <p>Status: <b>{{ r.status }}</b></p>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from "vue";
import api from "../services/api";

const error = ref("");
const myRequests = ref([]);
const form = ref({
  category: "food",
  title: "",
  description: "",
  region: "Moscow",
  requested_amount: 1000,
  urgency: 3,
});

async function loadMine() {
  try {
    error.value = "";
    const resp = await api.get("/api/requests/applicant/my/");
    myRequests.value = resp.data;
  } catch (e) {
    error.value = e?.response?.data?.detail || "Failed to load my requests";
  }
}

async function createRequest() {
  try {
    await api.post("/api/requests/applicant/create/", form.value);
    form.value.title = "";
    form.value.description = "";
    await loadMine();
  } catch (e) {
    alert(e?.response?.data?.detail || "Create failed");
  }
}

onMounted(loadMine);
</script>

<style scoped>
.card {
  border: 1px solid #ddd;
  border-radius: 10px;
  padding: 12px;
  margin-top: 10px;
  display: grid;
  gap: 8px;
}
label { display: grid; gap: 4px; }
.list { margin-top: 10px; display: grid; gap: 10px; }
.error { color: #b00020; }
</style>

