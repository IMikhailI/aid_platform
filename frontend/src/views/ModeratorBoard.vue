<template>
  <section>
    <h2>Moderator board: Queue</h2>
    <button @click="load">Refresh</button>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="items.length === 0">Queue is empty</div>
    <div class="list">
      <article class="card" v-for="r in items" :key="r.id">
        <h3>#{{ r.id }} — {{ r.title }}</h3>
        <p><b>Applicant:</b> {{ r.applicant_username }}</p>
        <p><b>Category:</b> {{ r.category }} | <b>Region:</b> {{ r.region }}</p>
        <p><b>Status:</b> {{ r.status }}</p>
        <div class="row">
          <button @click="moderate(r.id, 'approve')">Approve</button>
          <button @click="moderate(r.id, 'reject')">Reject</button>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from "vue";
import api from "../services/api";

const items = ref([]);
const error = ref("");

async function load() {
  try {
    error.value = "";
    const resp = await api.get("/api/requests/moderation/queue/");
    items.value = resp.data?.results ?? resp.data ?? [];
  } catch (e) {
    error.value = e?.response?.data?.detail || "Failed to load queue";
  }
}

async function moderate(id, action) {
  try {
    await api.post(`/api/requests/moderation/${id}/`, { action, comment: "From UI" });
    await load();
  } catch (e) {
    alert(e?.response?.data?.detail || "Action failed");
  }
}

onMounted(load);
</script>

<style scoped>
.list { display: grid; gap: 12px; margin-top: 12px; }
.card { border: 1px solid #ddd; border-radius: 10px; padding: 12px; }
.row { display: flex; gap: 8px; }
.error { color: #b00020; }
</style>
