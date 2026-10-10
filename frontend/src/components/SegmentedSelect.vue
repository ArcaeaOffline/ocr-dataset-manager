<script setup lang="ts" generic="T extends number | string | null">
const props = defineProps<{
  label: string;
  options: { value: T; label: string }[];
  modelValue: T;
  /** shown below the segments, e.g. a low-confidence prefill warning */
  hint?: string | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: T];
}>();

function pick(value: T) {
  // clicking the active segment clears (same as "未知")
  emit("update:modelValue", (props.modelValue === value ? null : value) as T);
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
    <p v-if="props.hint" class="mt-1 text-xs text-destructive">{{ props.hint }}</p>
  </div>
</template>
