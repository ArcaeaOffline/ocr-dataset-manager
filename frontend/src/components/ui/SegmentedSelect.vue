<script setup lang="ts" generic="T extends number | string | null">
import { computed } from "vue";
import { ToggleGroupItem, ToggleGroupRoot } from "reka-ui";
import FieldLabel from "./FieldLabel.vue";

const props = defineProps<{
  label: string;
  options: { value: T; label: string }[];
  modelValue: T;
  /** shown below the segments, e.g. a low-confidence prefill warning */
  hint?: string | null;
  /** the value is the machine prefill proposal. Shows a marker by the label */
  prefilled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: T];
}>();

// reka's pressed check treats a nullish group value as "nothing selected",
// so an option with value null can never render pressed. The "unknown"
// option rides on a sentinel instead. Option values are ids and small
// numbers and never collide with this string.
const NULL_VALUE = "__odm-null__";

const groupValue = computed(() => props.modelValue ?? NULL_VALUE);

// re-clicking the active segment emits undefined in reka. It and the
// sentinel-bound "unknown" both clear to null
function onGroupUpdate(value: unknown) {
  emit("update:modelValue", (value === NULL_VALUE || value == null ? null : value) as T);
}
</script>

<template>
  <div>
    <FieldLabel :label="props.label" :prefilled="props.prefilled" />
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
        class="segment-state px-2.5 py-1 text-sm"
      >
        {{ opt.label }}
      </ToggleGroupItem>
    </ToggleGroupRoot>
    <p v-if="props.hint" class="mt-1 text-xs text-destructive">{{ props.hint }}</p>
  </div>
</template>
