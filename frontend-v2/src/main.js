import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./assets/styles/base.css";
import "./assets/styles/landing.css";
import "./assets/styles/app.css";
import "./assets/styles/auth.css";
import "./assets/styles/helper.css";
import "./assets/styles/helper-requests.css";
import "./assets/styles/helper-my-help.css";
import "./assets/styles/applicant.css";
import "./assets/styles/moderator.css";

createApp(App).use(router).mount("#app");

window.addEventListener("auth:logout", () => {
  if (router.currentRoute.value.meta.auth) router.replace("/login");
});
