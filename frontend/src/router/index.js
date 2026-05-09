import { createRouter, createWebHistory } from "vue-router";
import { getRole, isAuthenticated } from "../services/auth";

import LoginPage from "../views/LoginPage.vue";
import HelperBoard from "../views/HelperBoard.vue";
import ModeratorBoard from "../views/ModeratorBoard.vue";
import ApplicantBoard from "../views/ApplicantBoard.vue";

const routes = [
  { path: "/", redirect: "/login" },
  { path: "/login", component: LoginPage },
  { path: "/helper", component: HelperBoard, meta: { auth: true, role: "helper" } },
  { path: "/moderator", component: ModeratorBoard, meta: { auth: true, role: ["moderator", "admin"] } },
  { path: "/applicant", component: ApplicantBoard, meta: { auth: true, role: "applicant" } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  if (!to.meta.auth) return next();

  if (!isAuthenticated()) return next("/login");

  const role = getRole();
  const allowedRoles = Array.isArray(to.meta.role) ? to.meta.role : [to.meta.role];
  if (to.meta.role && !allowedRoles.includes(role)) {
    if (role === "helper") return next("/helper");
    if (role === "moderator" || role === "admin") return next("/moderator");
    if (role === "applicant") return next("/applicant");
    return next("/login");
  }

  return next();
});

export default router;
