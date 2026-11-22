import { createRouter, createWebHistory } from "vue-router";

import AnnotateView from "./views/AnnotateView.vue";
import ExportView from "./views/ExportView.vue";
import ImportView from "./views/ImportView.vue";
import QueueView from "./views/QueueView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: QueueView },
    { path: "/import", component: ImportView },
    { path: "/export", component: ExportView },
    { path: "/annotate/:id", component: AnnotateView },
  ],
});
