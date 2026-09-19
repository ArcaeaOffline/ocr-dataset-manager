<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";

const emit = defineEmits<{ close: [] }>();

function onKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") emit("close");
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => window.removeEventListener("keydown", onKeydown));
</script>

<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 sm:p-6"
      @click.self="emit('close')"
    >
      <div
        class="flex max-h-full w-full max-w-[560px] flex-col rounded-lg border border-border bg-card p-4 shadow-xl"
      >
        <slot />
      </div>
    </div>
  </Teleport>
</template>
