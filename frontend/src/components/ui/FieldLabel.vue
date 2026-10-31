<script setup lang="ts">
const props = defineProps<{
  label: string;
  /** the value is the machine prefill proposal. Shows a marker by the label */
  prefilled?: boolean;
}>();
</script>

<template>
  <span class="field-label">
    {{ props.label }}
    <span
      v-if="props.prefilled"
      class="ml-0.5 inline-block size-1.5 rounded-full bg-warning align-middle"
      title="OCR 预识别"
    />
  </span>
</template>
