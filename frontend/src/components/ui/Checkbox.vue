<script setup lang="ts">
import { CheckboxIndicator, CheckboxRoot } from "reka-ui";

const props = defineProps<{
  modelValue: boolean;
  label: string;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();

function onUpdate(value: boolean | "indeterminate") {
  emit("update:modelValue", value === true);
}
</script>

<template>
  <label class="flex cursor-pointer items-center gap-1">
    <CheckboxRoot
      class="focus-ring size-4 rounded border border-input bg-background data-[state=checked]:border-primary data-[state=checked]:bg-primary"
      :model-value="props.modelValue"
      @update:model-value="onUpdate"
    >
      <CheckboxIndicator class="flex items-center justify-center">
        <i class="i-lucide-check size-4 text-primary-foreground" />
      </CheckboxIndicator>
    </CheckboxRoot>
    <span class="field-label">{{ props.label }}</span>
  </label>
</template>
