<script setup lang="ts">
import { ref } from "vue";
import { Toaster } from "vue-sonner";

type ThemeChoice = "auto" | "light" | "dark";
const THEME_KEY = "theme";

const stored = localStorage.getItem(THEME_KEY);
const theme = ref<ThemeChoice>(stored === "light" || stored === "dark" ? stored : "auto");
// applied in setup, before first paint, to avoid a flash of the wrong theme
if (theme.value !== "auto") {
  document.documentElement.dataset.theme = theme.value;
}

let transitionTimer: ReturnType<typeof setTimeout> | undefined;

function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  root.classList.add("theme-transition");
  clearTimeout(transitionTimer);
  transitionTimer = setTimeout(() => root.classList.remove("theme-transition"), 300);

  theme.value = choice;
  if (choice === "auto") {
    localStorage.removeItem(THEME_KEY);
    delete root.dataset.theme;
  } else {
    localStorage.setItem(THEME_KEY, choice);
    root.dataset.theme = choice;
  }
}

const themeOptions: { value: ThemeChoice; icon: string; title: string }[] = [
  { value: "light", icon: "i-lucide-sun", title: "日间" },
  { value: "auto", icon: "i-lucide-monitor", title: "跟随系统" },
  { value: "dark", icon: "i-lucide-moon", title: "夜间" },
];
</script>

<template>
  <div class="mx-auto max-w-6xl px-4 pb-10">
    <header class="flex items-center gap-6 border-b border-border py-3">
      <span class="text-sm font-semibold">OCR Dataset Manager</span>
      <nav class="flex items-center gap-4 text-sm">
        <RouterLink to="/" class="flex items-center gap-1 hover:underline">
          <i class="i-lucide-images size-4" />
          队列
        </RouterLink>
        <RouterLink to="/import" class="flex items-center gap-1 hover:underline">
          <i class="i-lucide-folder-plus size-4" />
          导入
        </RouterLink>
      </nav>
      <div class="ml-auto flex items-center gap-2">
        <span class="field-label">主题</span>
        <div class="flex gap-1">
          <button
            v-for="opt in themeOptions"
            :key="opt.value"
            type="button"
            class="cursor-pointer rounded border p-1.5"
            :class="
              theme === opt.value
                ? 'border-primary bg-primary text-primary-fg'
                : 'border-border bg-secondary text-secondary-fg'
            "
            :title="opt.title"
            @click="applyTheme(opt.value)"
          >
            <i :class="`${opt.icon} size-4`" />
          </button>
        </div>
      </div>
    </header>
    <RouterView />
  </div>
  <Toaster position="top-center" richColors />
</template>
