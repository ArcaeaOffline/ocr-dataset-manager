<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { CollapsibleContent, CollapsibleRoot, CollapsibleTrigger } from "reka-ui";
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

// the wrapper animates between 0 and the measured panel height; the
// observer keeps the measurement current when the panel content changes
const panelEl = ref<HTMLElement | null>(null);
const panelHeight = ref(0);
let observer: ResizeObserver | undefined;
onMounted(() => {
  observer = new ResizeObserver(() => {
    panelHeight.value = panelEl.value?.scrollHeight ?? 0;
  });
  if (panelEl.value) observer.observe(panelEl.value);
});
onUnmounted(() => observer?.disconnect());
</script>

<template>
  <CollapsibleRoot v-model:open="open">
    <CollapsibleTrigger as-child>
      <button
        type="button"
        class="flex w-full cursor-pointer items-center justify-between gap-2 rounded border border-border bg-secondary px-2.5 py-1.5 text-sm text-secondary-fg"
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
    </CollapsibleTrigger>
    <!-- the animated wrapper sits one level below the reka content
         element: reka neutralizes transition-duration on its own element
         while measuring, which would kill the reveal animation -->
    <CollapsibleContent force-mount>
      <div
        class="overflow-hidden transition-[height] duration-200 ease-out"
        :style="{ height: `${open ? panelHeight : 0}px` }"
      >
        <div ref="panelEl" class="pt-2" :inert="!open">
          <div class="space-y-2 rounded border border-border bg-card p-2">
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
    </CollapsibleContent>
  </CollapsibleRoot>
</template>
