<script setup lang="ts" generic="T extends number | string | null">
import { computed } from "vue";
import { ToggleGroupItem, ToggleGroupRoot } from "reka-ui";

const props = defineProps<{
  label: string;
  options: { value: T; label: string }[];
  modelValue: T;
  /** shown below the segments, e.g. a low-confidence prefill warning */
  hint?: string | null;
  /** the value is the machine prefill proposal; shows a marker by the label */
  prefilled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: T];
}>();

// reka's pressed check treats a nullish group value as "nothing selected",
// so an option with value null can never render pressed; the "unknown"
// option rides on a sentinel instead. Option values are ids and small
// numbers and never collide with this string.
const NULL_VALUE = "__odm-null__";

const groupValue = computed(() => props.modelValue ?? NULL_VALUE);

// re-clicking the active segment emits undefined in reka; it and the
// sentinel-bound "unknown" both clear to null
function onGroupUpdate(value: unknown) {
  emit("update:modelValue", (value === NULL_VALUE || value == null ? null : value) as T);
}
</script>

<template>
  <div>
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
    <ToggleGroupRoot
      type="single"
      class="mt-1 flex flex-wrap gap-1"
      :model-value="groupValue"
      @update:model-value="onGroupUpdate"
    >
      <ToggleGroupItem
        v-for="opt in props.options"
        :key="String(opt.value)"
        :value="opt.value ?? NULL_VALUE"
        class="rounded border px-2.5 py-1 text-sm cursor-pointer data-[state=off]:border-border data-[state=off]:bg-secondary data-[state=off]:text-secondary-fg data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-fg"
      >
        {{ opt.label }}
      </ToggleGroupItem>
    </ToggleGroupRoot>
    <p v-if="props.hint" class="mt-1 text-xs text-destructive">{{ props.hint }}</p>
  </div>
</template>
