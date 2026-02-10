<template>
  <section>
    <h2>Helper board: Published requests</h2>

    <div class="filters">
      <input v-model="region" placeholder="Filter by region" />
      <select v-model="category">
        <option value="">All categories</option>
        <option value="food">food</option>
        <option value="children">children</option>
        <option value="medicine">medicine</option>
        <option value="clothes">clothes</option>
        <option value="other">other</option>
      </select>
      <button @click="load">Apply</button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="items.length === 0">No published requests</div>
    <div class="list">
      <article class="card" v-for="r in items" :key="r.id">
        <h3>#{{ r.id }} — {{ r.title }}</h3>
        <p><b>Category:</b> {{ r.category }} | <b>Region:</b> {{ r.region }}</p>
        <p><b>Amount:</b> {{ r.requested_amount }} | <b>Urgency:</b> {{ r.urgency }}</p>
        <p><b>Status:</b> {{ r.status }}</p>
        <button @click="take(r.id)">Take into work</button>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from "vue";
import api from "../services/api";

const items = ref([]);
const error = ref("");
const region = ref("");
const category = ref("");

async function load() {
  try {
    error.value = "";
    const params = {};
    if (region.value) params.region = region.value;
    if (category.value) params.category = category.value;

    const resp = await api.get("/api/requests/published/", { params });
    items.value = resp.data;
  } catch (e) {
    error.value = e?.response?.data?.detail || "Failed to load";
  }
}

async function take(id) {
  try {
    await api.post(`/api/requests/helper/take/${id}/`, {
      method: "certificate",
      note: "Taken from web UI",
    });
    await load();
    alert(`Request #${id} is now in progress`);
  } catch (e) {
    alert(e?.response?.data?.detail || "Failed to take");
  }
}

onMounted(load);
</script>

<style scoped>
.filters { display: flex; gap: 8px; margin-bottom: 16px; }
.list { display: grid; gap: 12px; }
.card { border: 1px solid #ddd; border-radius: 10px; padding: 12px; }
.error { color: #b00020; }
</style>

