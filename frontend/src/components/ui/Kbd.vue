<script setup lang="ts">
import { computed } from "vue";

/** chip fits on cards and secondary buttons; invert fits on filled
    primary buttons */
const props = withDefaults(
  defineProps<{
    variant?: "chip" | "invert";
  }>(),
  { variant: "chip" },
);

const shortcutClass = computed(() => (props.variant === "invert" ? "kbd-on-primary" : "kbd-chip"));
</script>

<template>
  <kbd :class="shortcutClass"><slot /></kbd>
</template>
