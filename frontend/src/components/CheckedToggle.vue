<script setup lang="ts">
import { Toggle } from "reka-ui";

const props = defineProps<{ modelValue: boolean }>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();
</script>

<template>
  <Toggle
    :model-value="props.modelValue"
    class="w-full cursor-pointer rounded border px-3 py-2 text-sm font-medium data-[state=off]:border-border data-[state=off]:bg-secondary data-[state=off]:text-secondary-fg data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-fg"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <i :class="props.modelValue ? 'i-lucide-check-check size-4' : 'i-lucide-check size-4'" />
    {{ props.modelValue ? "已确认（点击取消）" : "标记为确认" }}
  </Toggle>
</template>
