<script setup lang="ts">
import { computed, ref } from "vue";
import { catalog, type Candidate, type PartnerEntry } from "../api";
import Modal from "./Modal.vue";

const props = defineProps<{
  candidates: Candidate[];
  partners: PartnerEntry[];
  modelValue: string | null;
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const text = ref(props.modelValue ?? "");
const open = ref(false);
const panelOpen = ref(false);
const query = ref("");

function onInput(event: Event) {
  text.value = (event.target as HTMLInputElement).value;
  open.value = true;
  emit("update:modelValue", text.value.trim() === "" ? null : text.value);
}

function pick(id: string) {
  text.value = id;
  emit("update:modelValue", id);
  open.value = false;
}

function onBlur() {
  setTimeout(() => {
    open.value = false;
  }, 120);
}

const filteredPartners = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (q === "") return props.partners;
  return props.partners.filter((p) => p.id.toLowerCase().includes(q));
});

function selectFromPanel(id: string) {
  panelOpen.value = false;
  pick(id);
}
</script>

<template>
  <div class="relative">
    <div class="flex items-end gap-1">
      <label class="block flex-1">
        <span class="field-label">partner_id</span>
        <input
          class="field-input mt-0.5"
          :value="text"
          placeholder="留空 = 未知"
          @input="onInput"
          @focus="open = true"
          @blur="onBlur"
        />
      </label>
      <button class="btn-secondary" title="浏览全部搭档" @click="panelOpen = true">
        <i class="i-lucide-layout-grid size-4" />
        浏览
      </button>
    </div>
    <div
      v-if="open && props.candidates.length > 0"
      class="absolute z-10 mt-0.5 w-full overflow-y-auto rounded border border-border bg-card shadow-lg"
    >
      <button
        v-for="c in props.candidates"
        :key="c.image_id"
        type="button"
        class="flex w-full items-center gap-2 px-2 py-1.5 text-left text-sm hover:bg-secondary"
        @mousedown.prevent="pick(c.image_id)"
      >
        <img
          :src="catalog.partnerIconUrl(c.image_id)"
          class="h-6 w-6 rounded object-cover"
          :alt="c.image_id"
        />
        <span class="flex-1 font-mono">{{ c.image_id }}</span>
        <span class="text-xs text-muted-foreground"> {{ (c.confidence * 100).toFixed(1) }}% </span>
      </button>
    </div>

    <Modal v-if="panelOpen" @close="panelOpen = false">
      <h3 class="mb-2 text-sm font-semibold">选择搭档</h3>
      <input v-model="query" class="field-input" placeholder="按 id 过滤…" autofocus />
      <div class="mt-2 max-h-80 overflow-y-auto">
        <div class="grid grid-cols-5 gap-2">
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
    </Modal>
  </div>
</template>
