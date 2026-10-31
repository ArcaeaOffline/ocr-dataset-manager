<script setup lang="ts" generic="T">
import { computed, ref, useSlots, watch } from "vue";
import {
  ComboboxAnchor,
  ComboboxContent,
  ComboboxInput,
  ComboboxPortal,
  ComboboxRoot,
} from "reka-ui";
import type { Candidate } from "@/api";
import Button from "./Button.vue";
import FieldLabel from "./FieldLabel.vue";
import ModalDialog from "./ModalDialog.vue";

const props = withDefaults(
  defineProps<{
    label: string;
    modelValue: string | null;
    candidates: Candidate[];
    /** the value is the machine prefill proposal. Shows a marker by the label */
    prefilled?: boolean;
    /** free text is the value; this explains the empty-input meaning */
    placeholder: string;
    triggerIcon: string;
    triggerLabel: string;
    triggerTitle: string;
    panelTitle: string;
    panelPlaceholder: string;
    panelDescription: string;
    /** entries the browse panel lists and filters */
    panelItems: T[];
    /** both panel and dropdown filtering use this against the lowercased query */
    panelMatch: (item: T, query: string) => boolean;
    /** caps the panel list length */
    panelLimit?: number;
    /** caps the dropdown options filtered from the catalog by the typed text;
     * unset disables that section */
    textMatchLimit?: number;
    /** the panel data is still loading. Shows a spinner instead of a false
     * "no matches" */
    panelLoading?: boolean;
  }>(),
  { prefilled: false, panelLoading: false },
);

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const slots = useSlots();

const text = ref(props.modelValue ?? "");
const panelOpen = ref(false);
const query = ref("");

// free text is the value
watch(text, (value) => {
  emit("update:modelValue", value.trim() === "" ? null : value);
});

// prefill loads and card switches arrive after mount. The input is driven
// by `text`, so modelValue changes must sync back
watch(
  () => props.modelValue,
  (value) => {
    if (value !== text.value.trim()) text.value = value ?? "";
  },
);

// the single-select listbox deselects the picked candidate on re-click by
// emitting undefined. The field keeps its text in that case
function onSelect(value: unknown) {
  if (typeof value !== "string") return;
  text.value = value;
}

function select(id: string) {
  panelOpen.value = false;
  text.value = id;
}

const panelMatches = computed(() => {
  const q = query.value.trim().toLowerCase();
  const matched =
    q === "" ? props.panelItems : props.panelItems.filter((item) => props.panelMatch(item, q));
  return props.panelLimit ? matched.slice(0, props.panelLimit) : matched;
});

// an empty input proposes nothing, so the dropdown section only exists
// while text matches something
const textMatches = computed(() => {
  if (props.textMatchLimit === undefined) return [];
  const q = text.value.trim().toLowerCase();
  if (q === "") return [];
  return props.panelItems
    .filter((item) => props.panelMatch(item, q))
    .slice(0, props.textMatchLimit);
});
</script>

<template>
  <ComboboxRoot
    :model-value="props.modelValue"
    :reset-search-term-on-blur="false"
    :reset-search-term-on-select="false"
    ignore-filter
    open-on-focus
    @update:model-value="onSelect"
  >
    <ComboboxAnchor class="flex items-end gap-1">
      <label class="block flex-1">
        <FieldLabel :label="props.label" :prefilled="props.prefilled" />
        <div class="relative mt-0.5">
          <ComboboxInput
            v-model="text"
            class="field-input"
            :class="{ 'pr-8': !!slots.suffix }"
            :placeholder="props.placeholder"
          />
          <slot name="suffix" />
        </div>
      </label>
      <Button variant="secondary" :title="props.triggerTitle" @click="panelOpen = true">
        <i :class="`${props.triggerIcon} size-4`" />
        {{ props.triggerLabel }}
      </Button>
    </ComboboxAnchor>

    <!-- candidates are OCR proposals, not catalog entries, so they never
         filter against the typed text -->
    <ComboboxPortal v-if="props.candidates.length > 0 || textMatches.length > 0">
      <ComboboxContent
        position="popper"
        :side-offset="4"
        class="z-10 w-[var(--reka-popper-anchor-width)] overflow-y-auto rounded border border-border bg-card shadow-lg"
      >
        <slot name="options" :candidates="props.candidates" :text-matches="textMatches" />
      </ComboboxContent>
    </ComboboxPortal>
  </ComboboxRoot>

  <ModalDialog
    :open="panelOpen"
    :title="props.panelTitle"
    :max-width="560"
    :sr-description="props.panelDescription"
    @update:open="panelOpen = $event"
  >
    <input v-model="query" class="field-input" :placeholder="props.panelPlaceholder" autofocus />
    <div class="mt-2 max-h-80 overflow-y-auto">
      <slot name="panel" :matches="panelMatches" :select="select" />
      <div
        v-if="props.panelLoading"
        class="px-2 py-4 text-center text-sm text-muted-foreground"
        aria-busy="true"
      >
        <i class="i-lucide-loader-circle size-4 animate-spin" />
        加载中…
      </div>
      <div
        v-else-if="panelMatches.length === 0"
        class="px-2 py-4 text-center text-sm text-muted-foreground"
      >
        无匹配结果
      </div>
    </div>
  </ModalDialog>
</template>
