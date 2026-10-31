<script setup lang="ts">
import FieldLabel from "./FieldLabel.vue";

const props = defineProps<{
  label: string;
  modelValue: number | null;
  /** the value is the machine prefill proposal. Shows a marker by the label */
  prefilled?: boolean;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number | null];
}>();

function onInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value.trim();
  const parsed = raw === "" ? null : Number(raw);
  emit("update:modelValue", parsed !== null && Number.isFinite(parsed) ? parsed : null);
}
</script>

<template>
  <label class="block">
    <FieldLabel :label="props.label" :prefilled="props.prefilled" />
    <!-- optional annotate-view crop: a window onto this field's ROI -->
    <slot name="crop" />
    <!-- optional line above the input, e.g. the value as the screenshot renders it -->
    <slot name="input-extra" />
    <input
      class="field-input mt-0.5"
      type="number"
      :min="props.min"
      :max="props.max"
      :step="props.step"
      :disabled="props.disabled"
      :value="props.modelValue ?? ''"
      @input="onInput"
    />
  </label>
</template>
