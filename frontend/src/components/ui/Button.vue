<script setup lang="ts">
import { computed } from "vue";
import { Primitive } from "reka-ui";

const props = withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "destructive";
  }>(),
  { variant: "primary" },
);

const variantShortcut = computed(() =>
  props.variant === "primary"
    ? "btn"
    : props.variant === "secondary"
      ? "btn-secondary"
      : "btn-destructive",
);
</script>

<template>
  <Primitive as="button" :class="variantShortcut">
    <slot />
  </Primitive>
</template>
