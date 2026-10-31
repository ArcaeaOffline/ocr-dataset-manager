<script setup lang="ts">
import { DialogContent, DialogDescription, DialogPortal, DialogRoot, DialogTitle } from "reka-ui";

const props = defineProps<{
  open: boolean;
  /** screen-reader title; the header slot carries the visible caption */
  title: string;
  /** screen-reader description */
  description?: string;
}>();

const emit = defineEmits<{ close: [] }>();
</script>

<template>
  <DialogRoot :open="props.open" @update:open="(value) => !value && emit('close')">
    <DialogPortal>
      <DialogContent class="fixed inset-0 z-50 flex flex-col bg-black/90 focus:outline-none">
        <DialogTitle class="sr-only">{{ props.title }}</DialogTitle>
        <DialogDescription class="sr-only">{{ props.description }}</DialogDescription>
        <div class="flex items-center justify-between gap-2 p-2 text-white">
          <slot name="header" />
          <div class="flex shrink-0 items-center gap-1">
            <slot name="actions" />
            <button type="button" class="btn-ghost-dark" title="关闭" @click="emit('close')">
              <i class="i-lucide-x size-4" />
            </button>
          </div>
        </div>
        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
