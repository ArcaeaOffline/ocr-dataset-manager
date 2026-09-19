<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api, type ImageItem } from "../api";

const uncheckedOnly = ref(true);
const page = ref(0);
const pageSize = 50;
const total = ref(0);
const items = ref<ImageItem[]>([]);
const loading = ref(false);

async function load() {
  loading.value = true;
  try {
    const data = await api.listImages(uncheckedOnly.value, page.value * pageSize, pageSize);
    items.value = data.items;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
}

watch([uncheckedOnly, page], load);
onMounted(load);

const pageCount = () => Math.max(1, Math.ceil(total.value / pageSize));
</script>

<template>
  <div class="py-4">
    <div class="mb-3 flex items-center gap-4 text-sm">
      <label class="flex items-center gap-1.5">
        <input v-model="uncheckedOnly" type="checkbox" />
        只看未标注
      </label>
      <span class="text-muted-foreground">共 {{ total }} 张</span>
      <span class="ml-auto flex items-center gap-2">
        <button class="btn-secondary" :disabled="page === 0 || loading" @click="page--">
          上一页
        </button>
        <span>{{ page + 1 }} / {{ pageCount() }}</span>
        <button
          class="btn-secondary"
          :disabled="(page + 1) * pageSize >= total || loading"
          @click="page++"
        >
          下一页
        </button>
      </span>
    </div>

    <div
      v-if="loading && items.length === 0"
      class="grid place-items-center py-16 text-muted-foreground"
      aria-busy="true"
    >
      <i class="i-lucide-loader-circle size-6 animate-spin" />
    </div>
    <div
      v-else
      class="grid grid-cols-5 gap-3"
      :class="{ 'pointer-events-none opacity-50': loading }"
    >
      <RouterLink
        v-for="item in items"
        :key="item.id"
        :to="`/annotate/${item.id}`"
        class="group block overflow-hidden rounded border border-border bg-card hover:border-ring"
      >
        <img
          v-if="item.has_thumbnail"
          :src="api.thumbUrl(item.id)"
          class="aspect-video w-full object-cover"
          loading="lazy"
        />
        <div
          v-else
          class="grid aspect-video w-full place-items-center text-xs text-muted-foreground"
        >
          无缩略图
        </div>
        <div class="truncate px-2 py-1 text-xs text-muted-foreground group-hover:text-foreground">
          {{ item.original_filename ?? item.id }}
        </div>
      </RouterLink>
    </div>
  </div>
</template>
