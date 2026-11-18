<script setup lang="ts">
import { computed } from "vue";

import { roiCropStyle, type FieldCrop } from "../lib/roiCropStyle";

const props = defineProps<
  FieldCrop & {
    /** width tier: crops fill their container up to the tier cap -
     * sm 84 px, md 128 px, lg 168 px - and shrink below it on narrow
     * containers. Defaults to lg */
    size?: "sm" | "md" | "lg";
  }
>();

const style = computed(() => roiCropStyle(props.rect, props.canvas));

const capClass = {
  sm: "max-w-21",
  md: "max-w-32",
  lg: "max-w-42",
} as const;

const widthClass = computed(() => `w-full ${capClass[props.size ?? "lg"]}`);
</script>

<template>
  <!-- the frame owns the border: percentage offsets resolve against the
       padding box, so a border on the aspect-ratio box would desync it
       from the rect aspect and shift the window vertically -->
  <div class="rounded border border-border bg-card" :class="widthClass">
    <!-- aspect-ratio fixes the box height from its width. The inner image
         overflows and is shifted so the rect region fills the box -->
    <div
      class="relative w-full overflow-hidden rounded-[inherit]"
      :style="{ aspectRatio: `${props.rect[2]} / ${props.rect[3]}` }"
    >
      <img
        :src="props.src"
        alt=""
        draggable="false"
        class="pointer-events-none absolute max-w-none select-none"
        :style="style"
      />
    </div>
  </div>
</template>
