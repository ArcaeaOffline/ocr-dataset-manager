<script setup lang="ts">
import { computed, ref } from "vue";
import type { Candidate } from "../api";

const props = defineProps<{
  label: string;
  modelValue: string | null;
  options: Candidate[];
}>();

const emit = defineEmits<{
  "update:modelValue": [value: string | null];
}>();

const text = ref(props.modelValue ?? "");
const open = ref(false);

// ihdb returns each image once per hash type; keep the best confidence
const deduped = computed(() => {
  const best = new Map<string, Candidate>();
  for (const c of props.options) {
    const prev = best.get(c.image_id);
    if (prev == null || prev.confidence < c.confidence) {
      best.set(c.image_id, c);
    }
  }
  return [...best.values()].sort((a, b) => b.confidence - a.confidence);
});

const filtered = computed(() => {
  const q = text.value.trim().toLowerCase();
  if (q === "") return deduped.value;
  return deduped.value.filter((c) => c.image_id.toLowerCase().includes(q));
});

function onInput(event: Event) {
  text.value = (event.target as HTMLInputElement).value;
  open.value = true;
  emit("update:modelValue", text.value.trim() === "" ? null : text.value);
}

function pick(candidate: Candidate) {
  text.value = candidate.image_id;
  emit("update:modelValue", candidate.image_id);
  open.value = false;
}

function onBlur() {
  // delay so option mousedown wins over the blur
  setTimeout(() => {
    open.value = false;
  }, 120);
}
</script>

<template>
  <div class="relative">
    <label class="block">
      <span class="field-label">{{ props.label }}</span>
      <input
        class="field-input mt-0.5"
        :value="text"
        placeholder="留空 = 未知"
        @input="onInput"
        @focus="open = true"
        @blur="onBlur"
      />
    </label>
    <div
      v-if="open && filtered.length > 0"
      class="absolute z-10 mt-0.5 max-h-64 w-full overflow-y-auto rounded border border-border bg-card shadow-lg"
    >
      <button
        v-for="c in filtered"
        :key="c.image_id"
        type="button"
        class="flex w-full items-center justify-between px-2 py-1.5 text-left text-sm hover:bg-secondary"
        @mousedown.prevent="pick(c)"
      >
        <span>{{ c.image_id }}</span>
        <span class="text-xs text-muted-foreground"> {{ (c.confidence * 100).toFixed(1) }}% </span>
      </button>
    </div>
  </div>
</template>
