import { createRouter, createWebHistory } from "vue-router";

import AnnotateView from "./views/AnnotateView.vue";
import ImportView from "./views/ImportView.vue";
import QueueView from "./views/QueueView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: QueueView },
    { path: "/import", component: ImportView },
    { path: "/annotate/:id", component: AnnotateView },
  ],
});
