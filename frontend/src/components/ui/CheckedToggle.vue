<script setup lang="ts">
import { Toggle } from "reka-ui";

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    /** label shown while unchecked */
    offLabel?: string;
    /** label shown while checked */
    onLabel?: string;
  }>(),
  { offLabel: "标记为确认", onLabel: "已确认（点击取消）" },
);

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();
</script>

<template>
  <Toggle
    :model-value="props.modelValue"
    class="segment-state w-full px-3 py-2 text-sm font-medium"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <i :class="props.modelValue ? 'i-lucide-check-check size-4' : 'i-lucide-check size-4'" />
    {{ props.modelValue ? props.onLabel : props.offLabel }}
  </Toggle>
</template>
