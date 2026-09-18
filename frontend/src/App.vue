<script setup lang="ts">
import { Toaster } from "vue-sonner";
</script>

<template>
  <div class="mx-auto max-w-6xl px-4 pb-10">
    <header class="flex items-center gap-6 border-b border-border py-3">
      <span class="text-sm font-semibold">OCR Dataset Manager</span>
      <nav class="flex gap-4 text-sm">
        <RouterLink to="/" class="hover:underline">队列</RouterLink>
        <RouterLink to="/import" class="hover:underline">导入</RouterLink>
      </nav>
    </header>
    <RouterView />
  </div>
  <Toaster position="top-center" richColors />
</template>
