<script setup lang="ts">
import { computed } from "vue";
import { Primitive } from "reka-ui";
import Kbd from "./Kbd.vue";

const props = withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "destructive";
    /** keyboard shortcut shown as a key cap after the label */
    shortcut?: string;
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

const kbdVariant = computed(() => (props.variant === "primary" ? "invert" : "chip"));
</script>

<template>
  <Primitive as="button" type="button" :class="variantShortcut">
    <slot />
    <Kbd v-if="props.shortcut" :variant="kbdVariant">{{ props.shortcut }}</Kbd>
  </Primitive>
</template>
