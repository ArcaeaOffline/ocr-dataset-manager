<script setup lang="ts">
import { computed, ref } from "vue";
import SegmentedSelect from "./SegmentedSelect.vue";

const props = defineProps<{
  flow: "device" | "b30";
  /** current b30 layout; the layout group renders only when layoutOptions
   * is given (device flow has no layout concept) */
  layout?: string | null;
  layoutOptions?: { value: string | null; label: string }[];
}>();

const emit = defineEmits<{
  switch: [flow: "device" | "b30"];
  changeLayout: [layout: string | null];
}>();

const open = ref(false);

const summary = computed(() =>
  props.flow === "b30" ? `B30/50 · ${props.layout ?? "布局未知"}` : "设备截图",
);

function onTypeChange(value: "device" | "b30") {
  emit("switch", value);
  open.value = false;
}

function onLayoutChange(value: string | null) {
  emit("changeLayout", value);
  open.value = false;
}

const typeOptions: { value: "device" | "b30"; label: string }[] = [
  { value: "device", label: "设备截图" },
  { value: "b30", label: "B30/50" },
];
</script>

<template>
  <div>
    <button
      type="button"
      class="flex w-full cursor-pointer items-center justify-between gap-2 rounded border border-border bg-secondary px-2.5 py-1.5 text-sm text-secondary-fg"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span
        class="flex items-center gap-1.5"
        :class="flow === 'b30' && layout == null ? 'text-destructive' : ''"
      >
        <i class="i-lucide-layers size-4" />
        {{ summary }}
      </span>
      <i
        class="i-lucide-chevron-down size-4 transition-transform"
        :class="{ 'rotate-180': open }"
      />
    </button>
    <!-- grid-rows 0fr→1fr animates the reveal without measuring height -->
    <div
      class="grid transition-[grid-template-rows] duration-150"
      :class="open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
    >
      <div class="overflow-hidden">
        <div class="space-y-2 pt-2">
          <SegmentedSelect
            :model-value="flow"
            label="类型"
            :options="typeOptions"
            @update:model-value="onTypeChange"
          />
          <SegmentedSelect
            v-if="layoutOptions"
            :model-value="layout ?? null"
            label="layout"
            :options="layoutOptions"
            @update:model-value="onLayoutChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>
