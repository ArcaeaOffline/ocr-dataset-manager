<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  ComboboxAnchor,
  ComboboxContent,
  ComboboxInput,
  ComboboxItem,
  ComboboxPortal,
  ComboboxRoot,
  DialogContent,
  DialogDescription,
  DialogOverlay,
  DialogPortal,
  DialogRoot,
  DialogTitle,
} from "reka-ui";
import { catalog, type Candidate, type PartnerEntry } from "../api";
import Button from "./Button.vue";

const props = defineProps<{
  candidates: Candidate[];
  partners: PartnerEntry[];
  modelValue: string | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const text = ref(props.modelValue ?? "");
const panelOpen = ref(false);
const query = ref("");

// free text is the value
watch(text, (value) => {
  emit("update:modelValue", value.trim() === "" ? null : value);
});

// the single-select listbox deselects the picked candidate on re-click by
// emitting undefined; the field keeps its text in that case
function onSelect(value: unknown) {
  if (typeof value !== "string") return;
  text.value = value;
}

const filteredPartners = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (q === "") return props.partners;
  return props.partners.filter((p) => p.id.toLowerCase().includes(q));
});

function selectFromPanel(id: string) {
  panelOpen.value = false;
  text.value = id;
}
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
        <span class="field-label">partner_id</span>
        <ComboboxInput v-model="text" class="field-input mt-0.5" placeholder="留空 = 未知" />
      </label>
      <Button variant="secondary" title="浏览全部搭档" @click="panelOpen = true">
        <i class="i-lucide-layout-grid size-4" />
        浏览
      </Button>
    </ComboboxAnchor>

    <!-- candidates are OCR proposals, not catalog entries, so they never
         filter against the typed text -->
    <ComboboxPortal v-if="props.candidates.length > 0">
      <ComboboxContent
        position="popper"
        :side-offset="4"
        class="z-10 w-[var(--reka-popper-anchor-width)] overflow-y-auto rounded border border-border bg-card shadow-lg"
      >
        <ComboboxItem
          v-for="c in props.candidates"
          :key="c.image_id"
          :value="c.image_id"
          class="flex cursor-pointer items-center gap-2 px-2 py-1.5 text-left text-sm data-[highlighted]:bg-secondary"
        >
          <img
            :src="catalog.partnerIconUrl(c.image_id)"
            class="h-6 w-6 rounded object-cover"
            :alt="c.image_id"
          />
          <span class="flex-1 font-mono">{{ c.image_id }}</span>
          <span class="text-xs text-muted-foreground">
            {{ (c.confidence * 100).toFixed(1) }}%
          </span>
        </ComboboxItem>
      </ComboboxContent>
    </ComboboxPortal>
  </ComboboxRoot>

  <DialogRoot :open="panelOpen" @update:open="panelOpen = $event">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/60" />
      <DialogContent
        class="fixed left-1/2 top-1/2 z-50 max-h-full w-full max-w-[560px] -translate-x-1/2 -translate-y-1/2 rounded-lg border border-border bg-card p-4 shadow-xl focus:outline-none"
      >
        <DialogTitle class="mb-2 text-sm font-semibold">选择搭档</DialogTitle>
        <DialogDescription class="sr-only">按 id 过滤，点击头像选择</DialogDescription>
        <input v-model="query" class="field-input" placeholder="按 id 过滤…" autofocus />
        <div class="mt-2 max-h-80 overflow-y-auto">
          <div class="grid grid-cols-3 gap-2 sm:grid-cols-5">
            <button
              v-for="p in filteredPartners"
              :key="p.id"
              type="button"
              class="rounded border border-border p-1 hover:border-ring"
              @click="selectFromPanel(p.id)"
            >
              <img
                :src="catalog.partnerIconUrl(p.id)"
                class="aspect-square w-full rounded object-cover"
                :alt="p.id"
                loading="lazy"
              />
              <div class="mt-0.5 text-center font-mono text-xs text-muted-foreground">
                {{ p.id }}
              </div>
            </button>
          </div>
          <div
            v-if="filteredPartners.length === 0"
            class="px-2 py-4 text-center text-sm text-muted-foreground"
          >
            无匹配结果
          </div>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
