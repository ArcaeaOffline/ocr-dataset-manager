<script setup lang="ts">
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import { api, type ImageItem, type QueueKind } from "../api";
import { useRequest } from "../composables/useRequest";

const uncheckedOnly = ref(true);
const kind = ref<QueueKind | null>(null);
const page = ref(0);
const pageSize = 50;

const kindOptions: { value: QueueKind | null; label: string }[] = [
  { value: null, label: "全部" },
  { value: "device", label: "device" },
  { value: "b30", label: "B30/50" },
  { value: "unclassified", label: "未分类" },
];

const { data, loading } = useRequest(
  () => [uncheckedOnly.value, kind.value, page.value] as const,
  ([unchecked, k, p]) =>
    api.listImages(unchecked, p * pageSize, pageSize, k).then((res) => ({
      items: res.items,
      total: res.total,
    })),
  {
    initialData: { items: [] as ImageItem[], total: 0 },
    onError: (e) => toast.error(`加载失败：${e.message}`),
  },
);

const items = computed(() => data.value.items);
const total = computed(() => data.value.total);
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

// thumbnails always exist after import; a load error means the file is
// gone from disk, which the <img> error event reports
const thumbFailed = ref<Record<string, true>>({});
</script>

<template>
  <div class="py-4">
    <div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
      <label class="flex items-center gap-1.5 whitespace-nowrap">
        <input v-model="uncheckedOnly" type="checkbox" />
        只看未标注
      </label>
      <div class="flex items-center gap-1">
        <button
          v-for="opt in kindOptions"
          :key="String(opt.value)"
          type="button"
          class="cursor-pointer rounded border px-2 py-0.5 text-xs"
          :class="
            kind === opt.value
              ? 'border-primary bg-primary text-primary-fg'
              : 'border-border bg-secondary text-secondary-fg'
          "
          @click="
            page = 0;
            kind = opt.value;
          "
        >
          {{ opt.label }}
        </button>
      </div>
      <span class="whitespace-nowrap text-muted-foreground">共 {{ total }} 张</span>
      <span class="ml-auto flex items-center gap-2 whitespace-nowrap">
        <button class="btn-secondary" :disabled="page === 0 || loading" @click="page--">
          上一页
        </button>
        <span>{{ page + 1 }} / {{ pageCount }}</span>
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
      class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
      :class="{ 'pointer-events-none opacity-50': loading }"
    >
      <RouterLink
        v-for="item in items"
        :key="item.id"
        :to="`/annotate/${item.id}`"
        class="group block overflow-hidden rounded border border-border bg-card hover:border-ring"
      >
        <img
          v-if="!thumbFailed[item.id]"
          :src="api.thumbUrl(item.id)"
          class="aspect-video w-full object-cover"
          loading="lazy"
          @error="thumbFailed[item.id] = true"
        />
        <div
          v-else
          class="grid aspect-video w-full place-items-center text-xs text-muted-foreground"
        >
          无缩略图
        </div>
        <div
          class="flex items-center justify-between gap-1 px-2 py-1 text-xs text-muted-foreground group-hover:text-foreground"
        >
          <span class="truncate">{{ item.original_filename ?? item.id }}</span>
          <span
            v-if="item.kind !== 'device'"
            class="shrink-0 rounded border border-border px-1 text-[10px]"
          >
            {{ item.kind === "b30" ? "B30/50" : "未分类" }}
          </span>
        </div>
      </RouterLink>
    </div>
  </div>
</template>
