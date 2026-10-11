<script setup lang="ts">
import {
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from "reka-ui";

const props = defineProps<{
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  /** confirm button renders in the destructive palette */
  destructive?: boolean;
  /** disables both buttons while the confirmed action runs */
  busy?: boolean;
}>();

const emit = defineEmits<{
  "update:open": [open: boolean];
  confirm: [];
}>();
</script>

<template>
  <DialogRoot :open="props.open" @update:open="emit('update:open', $event)">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/60" />
      <DialogContent
        class="fixed left-1/2 top-1/2 z-50 w-full max-w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-4 shadow-xl focus:outline-none"
      >
        <DialogTitle class="text-sm font-semibold">{{ props.title }}</DialogTitle>
        <DialogDescription class="mt-1 text-sm text-muted-foreground">
          {{ props.description }}
        </DialogDescription>
        <div class="mt-4 flex justify-end gap-2">
          <DialogClose as-child>
            <button
              type="button"
              class="btn-secondary"
              :disabled="props.busy"
              @click="emit('update:open', false)"
            >
              {{ props.cancelLabel ?? "取消" }}
            </button>
          </DialogClose>
          <button
            type="button"
            class="inline-flex cursor-pointer items-center justify-center gap-1.5 whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium disabled:opacity-50"
            :class="
              props.destructive
                ? 'bg-destructive text-destructive-fg'
                : 'bg-primary text-primary-fg'
            "
            :disabled="props.busy"
            @click="emit('confirm')"
          >
            {{ props.confirmLabel }}
          </button>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
