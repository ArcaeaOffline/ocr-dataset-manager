<script setup lang="ts">
import { Toggle } from "reka-ui";
import Kbd from "./Kbd.vue";

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
    class="segment-state flex w-full items-center justify-center gap-1.5 px-3 py-2 text-sm font-medium"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="flex-grow-1" />
    <i :class="props.modelValue ? 'i-lucide-check-check size-4' : 'i-lucide-check size-4'" />
    {{ props.modelValue ? props.onLabel : props.offLabel }}
    <div class="flex-grow-1" />
    <Kbd :variant="props.modelValue ? 'invert' : 'chip'">T</Kbd>
  </Toggle>
</template>
