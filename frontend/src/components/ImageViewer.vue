<script setup lang="ts">
import { ref, watch } from "vue";
import { DialogContent, DialogDescription, DialogPortal, DialogRoot, DialogTitle } from "reka-ui";

const props = defineProps<{
  open: boolean;
  src: string;
  alt?: string;
  /** header caption, usually the filename */
  label?: string | null;
}>();

const emit = defineEmits<{ close: [] }>();

const ZOOM_LEVELS = [1, 2, 3, 4];
const zoomIdx = ref(0);

watch(
  () => props.open,
  (opened) => {
    if (opened) zoomIdx.value = 0;
  },
);
</script>

<template>
  <DialogRoot :open="props.open" @update:open="(value) => !value && emit('close')">
    <DialogPortal>
      <DialogContent class="fixed inset-0 z-50 flex flex-col bg-black/90 focus:outline-none">
        <DialogTitle class="sr-only">{{ props.label }}</DialogTitle>
        <DialogDescription class="sr-only">{{ props.alt }}</DialogDescription>
        <div class="flex items-center justify-between gap-2 p-2 text-white">
          <span class="truncate text-xs">{{ props.label }}</span>
          <div class="flex shrink-0 items-center gap-1">
            <button
              type="button"
              class="cursor-pointer rounded p-1.5 hover:bg-white/10 disabled:opacity-40"
              :disabled="zoomIdx === 0"
              @click="zoomIdx--"
            >
              <i class="i-lucide-zoom-out size-4" />
            </button>
            <span class="w-8 text-center text-xs tabular-nums"> {{ ZOOM_LEVELS[zoomIdx] }}x </span>
            <button
              type="button"
              class="cursor-pointer rounded p-1.5 hover:bg-white/10 disabled:opacity-40"
              :disabled="zoomIdx === ZOOM_LEVELS.length - 1"
              @click="zoomIdx++"
            >
              <i class="i-lucide-zoom-in size-4" />
            </button>
            <button
              type="button"
              class="cursor-pointer rounded p-1.5 hover:bg-white/10"
              @click="emit('close')"
            >
              <i class="i-lucide-x size-4" />
            </button>
          </div>
        </div>
        <!-- zoom via width scaling + native touch panning inside the scroll
             box, so page zoom is never touched -->
        <div class="flex-1 overflow-auto">
          <img
            :src="props.src"
            class="max-w-none"
            :style="{ width: `${ZOOM_LEVELS[zoomIdx] * 100}%` }"
            :alt="props.alt"
          />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
