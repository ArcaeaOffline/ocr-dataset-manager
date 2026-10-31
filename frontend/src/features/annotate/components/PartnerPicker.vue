<script setup lang="ts">
import { computed } from "vue";
import { ComboboxItem } from "reka-ui";
import { catalog, type Candidate, type PartnerEntry } from "@/api";
import ComboboxPicker from "@/components/ui/ComboboxPicker.vue";

const props = defineProps<{
  candidates: Candidate[];
  partners: PartnerEntry[];
  modelValue: string | null;
  /** the value is the machine prefill proposal. Shows a marker by the label */
  prefilled?: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

// the typed id or name resolves to a partner for the avatar preview
const selectedPartner = computed(() => {
  const t = props.modelValue?.trim().toLowerCase() ?? "";
  if (t === "") return null;
  return (
    props.partners.find((p) => p.id.toLowerCase() === t) ??
    props.partners.find((p) => p.name?.toLowerCase() === t) ??
    null
  );
});

const partnersById = computed(() => new Map(props.partners.map((p) => [p.id, p])));

// keep human friendly letter id first
function partnerLabel(p: PartnerEntry) {
  return p.name ? `${p.name} · ${p.id}` : p.id;
}

// candidates are icon stems. Only the id is known before the catalog loads
function candidateLabel(imageId: string) {
  return partnerLabel(partnersById.value.get(imageId) ?? { id: imageId, name: null });
}
</script>

<template>
  <ComboboxPicker
    :candidates="props.candidates"
    :model-value="props.modelValue"
    :prefilled="props.prefilled"
    label="partner_id"
    placeholder="留空 = 未知"
    trigger-icon="i-lucide-layout-grid"
    trigger-label="浏览"
    trigger-title="浏览全部搭档"
    panel-title="选择搭档"
    panel-placeholder="按 id 过滤…"
    panel-description="按 id 过滤，点击头像选择"
    :panel-items="props.partners"
    :panel-match="
      (p, q) => p.id.toLowerCase().includes(q) || (p.name ?? '').toLowerCase().includes(q)
    "
    :text-match-limit="8"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #suffix>
      <img
        v-if="selectedPartner"
        :src="catalog.partnerIconUrl(selectedPartner.id)"
        class="pointer-events-none absolute right-1.5 top-1/2 size-6 -translate-y-1/2 rounded object-cover"
        :alt="selectedPartner.name ?? selectedPartner.id"
      />
    </template>
    <template #options="{ candidates, textMatches }">
      <ComboboxItem
        v-for="c in candidates"
        :key="c.image_id"
        :value="c.image_id"
        class="combobox-item"
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
      <template v-if="textMatches.length > 0">
        <div v-if="candidates.length > 0" class="border-t border-border" />
        <ComboboxItem
          v-for="p in textMatches"
          :key="`partner-${p.id}`"
          :value="p.id"
          class="combobox-item"
        >
          <img
            :src="catalog.partnerIconUrl(p.id)"
            class="h-6 w-6 rounded object-cover"
            :alt="p.id"
          />
          <span class="flex-1 truncate font-mono">{{ partnerLabel(p) }}</span>
        </ComboboxItem>
      </template>
    </template>
    <template #panel="{ matches, select }">
      <div class="grid grid-cols-3 gap-2 sm:grid-cols-5">
        <button
          v-for="p in matches"
          :key="p.id"
          type="button"
          class="rounded border border-border p-1 hover:border-ring"
          @click="select(p.id)"
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
    </template>
  </ComboboxPicker>
</template>
