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
import { catalog, type Candidate, type PartnerEntry } from "@/api";
import Button from "@/components/ui/Button.vue";

const props = defineProps<{
  candidates: Candidate[];
  partners: PartnerEntry[];
  modelValue: string | null;
  /** the value is the machine prefill proposal; shows a marker by the label */
  prefilled?: boolean;
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

// prefill fills partner_id after mount (flow switch fetches it separately);
// the input is driven by `text`, so modelValue changes must sync back
watch(
  () => props.modelValue,
  (value) => {
    if (value !== text.value.trim()) text.value = value ?? "";
  },
);

// the single-select listbox deselects the picked candidate on re-click by
// emitting undefined; the field keeps its text in that case
function onSelect(value: unknown) {
  if (typeof value !== "string") return;
  text.value = value;
}

const filteredPartners = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (q === "") return props.partners;
  return props.partners.filter(
    (p) => p.id.toLowerCase().includes(q) || (p.name ?? "").toLowerCase().includes(q),
  );
});

// an empty input proposes nothing; the browse dialog covers the full list
const catalogMatches = computed(() => {
  const q = text.value.trim().toLowerCase();
  if (q === "") return [];
  return props.partners
    .filter(
      (p) => p.id.toLowerCase().includes(q) || (p.name ?? "").toLowerCase().includes(q),
    )
    .slice(0, 8);
});

const selectedPartner = computed(() => {
  const t = text.value.trim().toLowerCase();
  if (t === "") return null;
  return (
    props.partners.find((p) => p.id.toLowerCase() === t) ??
    props.partners.find((p) => p.name?.toLowerCase() === t) ??
    null
  );
});

const partnersById = computed(() => new Map(props.partners.map((p) => [p.id, p])));

// letter id first — it is the human-friendly form
function partnerLabel(p: PartnerEntry) {
  return p.name ? `${p.name} · ${p.id}` : p.id;
}

// candidates are icon stems; only the id is known before the catalog loads
function candidateLabel(imageId: string) {
  return partnerLabel(partnersById.value.get(imageId) ?? { id: imageId, name: null });
}

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
        <span class="field-label">
          partner_id
          <span
            v-if="props.prefilled"
            class="ml-0.5 inline-block size-1.5 rounded-full bg-amber-500 align-middle"
            title="OCR 预识别"
          />
        </span>
        <div class="relative mt-0.5">
          <ComboboxInput v-model="text" class="field-input pr-8" placeholder="留空 = 未知" />
          <img
            v-if="selectedPartner"
            :src="catalog.partnerIconUrl(selectedPartner.id)"
            class="pointer-events-none absolute right-1.5 top-1/2 size-6 -translate-y-1/2 rounded object-cover"
            :alt="selectedPartner.name ?? selectedPartner.id"
          />
        </div>
      </label>
      <Button variant="secondary" title="浏览全部搭档" @click="panelOpen = true">
        <i class="i-lucide-layout-grid size-4" />
        浏览
      </Button>
    </ComboboxAnchor>

    <!-- OCR candidates are proposals, not catalog entries, so they never
         filter against the typed text; the catalog section below does -->
    <ComboboxPortal v-if="props.candidates.length > 0 || catalogMatches.length > 0">
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
          <span class="flex-1 truncate font-mono">{{ candidateLabel(c.image_id) }}</span>
          <span class="shrink-0 text-xs text-muted-foreground">
            {{ (c.confidence * 100).toFixed(1) }}%
          </span>
        </ComboboxItem>
        <template v-if="catalogMatches.length > 0">
          <div v-if="props.candidates.length > 0" class="border-t border-border" />
          <ComboboxItem
            v-for="p in catalogMatches"
            :key="`partner-${p.id}`"
            :value="p.id"
            class="flex cursor-pointer items-center gap-2 px-2 py-1.5 text-left text-sm data-[highlighted]:bg-secondary"
          >
            <img
              :src="catalog.partnerIconUrl(p.id)"
              class="h-6 w-6 rounded object-cover"
              :alt="p.id"
            />
            <span class="flex-1 truncate font-mono">{{ partnerLabel(p) }}</span>
          </ComboboxItem>
        </template>
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
                <div v-if="p.name" class="truncate" :title="p.name">{{ p.name }}</div>
                <div>{{ p.id }}</div>
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
