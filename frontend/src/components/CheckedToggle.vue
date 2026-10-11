<script setup lang="ts">
const props = defineProps<{ modelValue: boolean }>();

const emit = defineEmits<{
  "update:modelValue": [value: boolean];
}>();
</script>

<template>
  <button
    type="button"
    class="w-full cursor-pointer rounded border px-3 py-2 text-sm font-medium"
    :class="
      props.modelValue
        ? 'border-primary bg-primary text-primary-fg'
        : 'border-border bg-secondary text-secondary-fg'
    "
    @click="emit('update:modelValue', !props.modelValue)"
  >
    <i :class="props.modelValue ? 'i-lucide-check-check size-4' : 'i-lucide-check size-4'" />
    {{ props.modelValue ? "已确认（点击取消）" : "标记为确认" }}
  </button>
</template>
