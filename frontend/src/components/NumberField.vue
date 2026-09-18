<script setup lang="ts">
const props = defineProps<{
  label: string;
  modelValue: number | null;
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
    <span class="field-label">{{ props.label }}</span>
    <input
      class="field-input mt-0.5"
      type="number"
      :value="props.modelValue ?? ''"
      @input="onInput"
    />
  </label>
</template>
