<script setup lang="ts">
import { ref, watch } from "vue";
import FullscreenDialog from "@/components/ui/FullscreenDialog.vue";

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
  <FullscreenDialog
    :open="props.open"
    :title="props.label ?? ''"
    :description="props.alt"
    @close="emit('close')"
  >
    <template #header>
      <span class="truncate text-xs">{{ props.label }}</span>
    </template>
    <template #actions>
      <button type="button" class="btn-ghost-dark" :disabled="zoomIdx === 0" @click="zoomIdx--">
        <i class="i-lucide-zoom-out size-4" />
      </button>
      <span class="w-8 text-center text-xs tabular-nums"> {{ ZOOM_LEVELS[zoomIdx] }}x </span>
      <button
        type="button"
        class="btn-ghost-dark"
        :disabled="zoomIdx === ZOOM_LEVELS.length - 1"
        @click="zoomIdx++"
      >
        <i class="i-lucide-zoom-in size-4" />
      </button>
    </template>
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
  </FullscreenDialog>
</template>
