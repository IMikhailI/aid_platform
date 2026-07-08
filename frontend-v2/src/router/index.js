import { createRouter, createWebHistory } from "vue-router";
import { authStore } from "../stores/authStore";

const routes = [
  { path: "/", component: () => import("../pages/public/LandingPage.vue"), meta: { layout: "public" } },
  { path: "/login", component: () => import("../pages/auth/LoginPage.vue"), meta: { guest: true } },
  { path: "/register", component: () => import("../pages/auth/RegisterPage.vue"), meta: { guest: true } },
  {
    path: "/applicant",
    component: () => import("../layouts/ApplicantLayout.vue"),
    meta: { auth: true, roles: ["applicant"] },
    children: [
      { path: "", redirect: "/applicant/overview" },
      { path: "overview", component: () => import("../pages/applicant/ApplicantOverviewPage.vue") },
      { path: "requests", component: () => import("../pages/applicant/ApplicantRequestsPage.vue") },
      { path: "history", component: () => import("../pages/applicant/ApplicantAidHistoryPage.vue") },
      { path: "settings", component: () => import("../pages/applicant/ApplicantSettingsPage.vue") },
    ],
  },
  {
    path: "/helper",
    component: () => import("../layouts/HelperLayout.vue"),
    meta: { auth: true, roles: ["helper"] },
    children: [
      { path: "", redirect: "/helper/overview" },
      { path: "overview", component: () => import("../pages/helper/HelperOverviewPage.vue") },
      { path: "requests", component: () => import("../pages/helper/HelperRequestsPage.vue") },
      { path: "my-help", component: () => import("../pages/helper/HelperMyHelpPage.vue") },
      { path: "saved", component: () => import("../pages/helper/HelperSavedPage.vue") },
      { path: "settings", component: () => import("../pages/helper/HelperSettingsPage.vue") },
    ],
  },
  {
    path: "/moderator",
    component: () => import("../layouts/ModeratorLayout.vue"),
    meta: { auth: true, roles: ["moderator", "admin"] },
    children: [
      { path: "", redirect: "/moderator/pending" },
      { path: "pending", component: () => import("../pages/moderator/ModeratorPendingPage.vue") },
      { path: "approved", component: () => import("../pages/moderator/ModeratorApprovedPage.vue") },
      { path: "rejected", component: () => import("../pages/moderator/ModeratorRejectedPage.vue") },
    ],
  },
  { path: "/404", component: () => import("../pages/NotFoundPage.vue") },
  { path: "/:pathMatch(.*)*", redirect: "/404" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (to) => (to.hash ? { el: to.hash, top: 96, behavior: "smooth" } : { top: 0 }),
});

router.beforeEach(async (to) => {
  if ((to.meta.guest || to.meta.auth) && authStore.isAuthenticated.value && !authStore.state.initialized) {
    try {
      await authStore.fetchMe();
    } catch {
      authStore.logout();
    }
  }

  if (to.meta.guest && authStore.isAuthenticated.value) return authStore.redirectByRole();
  if (!to.meta.auth) return true;
  if (!authStore.isAuthenticated.value) return { path: "/login", query: { redirect: to.fullPath } };

  if (!to.meta.roles.includes(authStore.currentRole.value)) return authStore.redirectByRole();
  return true;
});

export default router;
