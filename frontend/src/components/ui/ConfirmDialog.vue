<script setup lang="ts">
import { DialogClose } from "reka-ui";
import Button from "./Button.vue";
import ModalDialog from "./ModalDialog.vue";

const props = defineProps<{
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  /** confirm button renders in the destructive palette */
  destructive?: boolean;
  /** blocks dismissal and disables both buttons while the confirmed action runs */
  busy?: boolean;
}>();

const emit = defineEmits<{
  "update:open": [open: boolean];
  confirm: [];
}>();
</script>

<template>
  <ModalDialog
    :open="props.open"
    :title="props.title"
    @update:open="(value) => !props.busy && emit('update:open', value)"
  >
    <template #description>{{ props.description }}</template>
    <div class="mt-4 flex justify-end gap-2">
      <DialogClose as-child>
        <Button variant="secondary" :disabled="props.busy" @click="emit('update:open', false)">
          {{ props.cancelLabel ?? "取消" }}
        </Button>
      </DialogClose>
      <Button
        :variant="props.destructive ? 'destructive' : 'primary'"
        :disabled="props.busy"
        @click="emit('confirm')"
      >
        {{ props.confirmLabel }}
      </Button>
    </div>
  </ModalDialog>
</template>
