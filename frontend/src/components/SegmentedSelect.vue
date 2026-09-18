<script setup lang="ts">
const props = defineProps<{
  label: string;
  options: { value: number | null; label: string }[];
  modelValue: number | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: number | null];
}>();

function pick(value: number | null) {
  // clicking the active segment clears (same as "未知")
  emit("update:modelValue", props.modelValue === value ? null : value);
}
</script>

<template>
  <div>
    <span class="field-label">{{ props.label }}</span>
    <div class="mt-1 flex flex-wrap gap-1">
      <button
        v-for="opt in props.options"
        :key="String(opt.value)"
        type="button"
        class="rounded border px-2.5 py-1 text-sm cursor-pointer"
        :class="
          props.modelValue === opt.value
            ? 'border-primary bg-primary text-primary-fg'
            : 'border-border bg-secondary text-secondary-fg'
        "
        @click="pick(opt.value)"
      >
        {{ opt.label }}
      </button>
    </div>
  </div>
</template>
