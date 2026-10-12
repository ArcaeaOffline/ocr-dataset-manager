<script setup lang="ts">
// the parent element needs `relative`; the mask is absolutely positioned
// over its full box
const props = withDefaults(
  defineProps<{
    /** backdrop color: page background or card surface */
    tone?: "page" | "card";
    /** spinner size, a size-* utility class */
    size?: string;
  }>(),
  { tone: "page", size: "size-6" },
);
</script>

<template>
  <div class="absolute inset-0 z-20 grid place-items-center" aria-busy="true">
    <div
      :class="props.tone === 'card' ? 'rounded bg-card' : 'bg-background'"
      class="absolute inset-0 opacity-80"
    />
    <i
      :class="props.size"
      class="i-lucide-loader-circle relative animate-spin text-muted-foreground"
    />
  </div>
</template>
