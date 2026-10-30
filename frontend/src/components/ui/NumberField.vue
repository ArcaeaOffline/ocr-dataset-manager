<script setup lang="ts">
const props = defineProps<{
  label: string;
  modelValue: number | null;
  /** the value is the machine prefill proposal; shows a marker by the label */
  prefilled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number | null];
}>();

function onInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value.trim();
  emit("update:modelValue", raw === "" ? null : Number(raw));
}
</script>

<template>
  <label class="block">
    <span class="field-label">
      {{ props.label }}
      <span
        v-if="props.prefilled"
        class="ml-0.5 inline-block size-1.5 rounded-full bg-amber-500 align-middle"
        title="OCR 预识别"
      />
    </span>
    <!-- optional annotate-view crop: a window onto this field's ROI -->
    <slot name="crop" />
    <input
      class="field-input mt-0.5"
      type="number"
      :value="props.modelValue ?? ''"
      @input="onInput"
    />
  </label>
</template>
