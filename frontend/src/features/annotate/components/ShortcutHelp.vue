<script setup lang="ts">
import Kbd from "@/components/ui/Kbd.vue";
import ModalDialog from "@/components/ui/ModalDialog.vue";

const props = defineProps<{ open: boolean }>();

const emit = defineEmits<{
  "update:open": [open: boolean];
}>();

interface HelpRow {
  label: string;
  keys: string[];
}

interface HelpGroup {
  title: string;
  rows: HelpRow[];
}

const groups: HelpGroup[] = [
  {
    title: "提交",
    rows: [
      { label: "保存，下一项", keys: ["Ctrl+Enter"] },
      { label: "保存，停在当前项", keys: ["Ctrl+S"] },
      { label: "跳过，下一项", keys: ["S"] },
      { label: "隐藏，下一项", keys: ["Ctrl+H"] },
    ],
  },
  {
    title: "字段",
    rows: [
      { label: "rating_class 难度", keys: ["1-5"] },
      { label: "clear_status 状态", keys: ["L", "C", "F", "P", "E", "H"] },
    ],
  },
  {
    title: "导航",
    rows: [
      { label: "上一卡 / 下一卡 (B30)", keys: ["←", "→"] },
      { label: "查看原图", keys: ["V"] },
      { label: "卡片总览 (B30)", keys: ["O"] },
      { label: "快捷键速查", keys: ["?"] },
    ],
  },
];
</script>

<template>
  <ModalDialog
    :open="props.open"
    title="快捷键"
    sr-description="标注页可用的键盘快捷键"
    @update:open="emit('update:open', $event)"
  >
    <div class="space-y-4">
      <section v-for="group in groups" :key="group.title">
        <p class="field-label mb-1.5">{{ group.title }}</p>
        <div class="space-y-1.5">
          <div
            v-for="row in group.rows"
            :key="row.label"
            class="flex items-center justify-between gap-4 text-sm"
          >
            <span>{{ row.label }}</span>
            <span class="flex shrink-0 items-center gap-1">
              <Kbd v-for="key in row.keys" :key="key">{{ key }}</Kbd>
            </span>
          </div>
        </div>
      </section>
      <p class="text-xs text-muted-foreground">再按已选字段的同一按键，清除回未知</p>
    </div>
  </ModalDialog>
</template>
