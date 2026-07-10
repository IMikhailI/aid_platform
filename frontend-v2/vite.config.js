import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  cacheDir: process.env.VITE_CACHE_DIR || "/tmp/aid-platform-vite-cache",
  plugins: [vue()],
});
