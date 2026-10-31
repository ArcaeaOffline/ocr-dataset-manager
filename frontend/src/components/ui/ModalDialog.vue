<script setup lang="ts">
import {
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from "reka-ui";

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    /** max content width in px */
    maxWidth?: number;
    /** accessible description for content that has no visible one */
    srDescription?: string;
  }>(),
  { maxWidth: 420, srDescription: "" },
);

const emit = defineEmits<{
  "update:open": [open: boolean];
}>();
</script>

<template>
  <DialogRoot :open="props.open" @update:open="emit('update:open', $event)">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/60" />
      <DialogContent
        class="fixed left-1/2 top-1/2 z-50 max-h-full w-full -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-4 shadow-xl focus:outline-none"
        :style="{ maxWidth: `${props.maxWidth}px` }"
      >
        <DialogTitle class="mb-2 text-sm font-semibold">{{ props.title }}</DialogTitle>
        <DialogDescription v-if="$slots.description" class="mt-1 text-sm text-muted-foreground">
          <slot name="description" />
        </DialogDescription>
        <DialogDescription v-else class="sr-only">{{ props.srDescription }}</DialogDescription>
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
