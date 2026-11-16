<script setup lang="ts">
import { computed, ref } from "vue";
import { toast } from "vue-sonner";
import { ToggleGroupItem, ToggleGroupRoot } from "reka-ui";
import { api, type ImageCategory, type ImageCounts, type ImageItem, type QueueKind } from "@/api";
import Button from "@/components/ui/Button.vue";
import { useRequest } from "@/composables/useRequest";

const category = ref<ImageCategory>("unchecked");
const kind = ref<QueueKind | null>(null);
const orderBy = ref<"created_at" | "original_filename">("created_at");
const direction = ref<"asc" | "desc">("desc");
const page = ref(0);
const pageSize = 50;

const kindOptions: { value: QueueKind | null; label: string }[] = [
  { value: null, label: "全部" },
  { value: "device", label: "device" },
  { value: "b30", label: "B30/50" },
  { value: "unclassified", label: "分类未知" },
];

const sortOptions: { value: "created_at" | "original_filename"; label: string }[] = [
  { value: "created_at", label: "时间" },
  { value: "original_filename", label: "文件名" },
];

const categoryItems: { value: ImageCategory; label: string; icon: string }[] = [
  { value: "all", label: "全部", icon: "i-lucide-images" },
  { value: "unchecked", label: "未标注", icon: "i-lucide-circle-dashed" },
  { value: "checked", label: "已标注", icon: "i-lucide-check" },
  { value: "hidden", label: "已隐藏", icon: "i-lucide-eye-off" },
];

// reka's pressed check treats a nullish group value as "nothing selected",
// so the null option rides on a sentinel, like SegmentedSelect does
const NULL_KIND = "__odm-null__";

function onKindUpdate(value: unknown) {
  page.value = 0;
  kind.value = value === NULL_KIND || value == null ? null : (value as QueueKind);
}

function selectCategory(value: ImageCategory) {
  category.value = value;
  page.value = 0;
}

// sort has no "unknown" state: re-clicking the active segment emits
// undefined in reka, which is ignored here instead of mapping onto a
// default. Anything else is a real switch and restarts pagination
function onSortUpdate(value: unknown) {
  if (value !== "created_at" && value !== "original_filename") return;
  orderBy.value = value;
  page.value = 0;
}

function toggleDirection() {
  direction.value = direction.value === "desc" ? "asc" : "desc";
  page.value = 0;
}

const { data: counts, refresh: refreshCounts } = useRequest(
  () => [kind.value] as const,
  ([k]) => api.imageCounts(k),
  {
    initialData: { all: 0, unchecked: 0, checked: 0, hidden: 0 } as ImageCounts,
    onError: (e) => toast.error(`加载计数失败：${e.message}`),
  },
);

// the request key carries the ordering params so sorting changes refetch
const { data, loading, refresh } = useRequest(
  () => [category.value, kind.value, orderBy.value, direction.value, page.value] as const,
  ([cat, k, ob, dir, p]) =>
    api
      .listImages(cat, p * pageSize, pageSize, k, { order_by: ob, direction: dir })
      .then((res) => ({
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

// traversal context forwarded to the annotate page: /next and /prev walk
// the same category slice in the same order the queue lists. The hidden
// view has no walk, so nothing is passed there and the endpoint defaults
// apply
const annotateQuery = computed(() =>
  category.value === "hidden"
    ? {}
    : { category: category.value, order_by: orderBy.value, direction: direction.value },
);

// thumbnails always exist after import. A load error means the file is
// gone from disk, which the <img> error event reports
const thumbFailed = ref<Record<string, true>>({});

// checked === true covers both flows: device carries the row flag, b30
// carries the derived all-components-checked state
function isDone(item: ImageItem): boolean {
  return item.checked === true;
}

function isDraft(item: ImageItem): boolean {
  return item.kind === "device" && item.checked === false;
}

function b30Progress(item: ImageItem): string | null {
  if (item.kind !== "b30" || item.checked !== false || item.b30_component_count == null) {
    return null;
  }
  return `${item.b30_checked_count ?? 0}/${item.b30_component_count}`;
}

async function toggleHidden(item: ImageItem) {
  try {
    await api.setImageHidden(item.id, !item.hidden);
  } catch (e) {
    toast.error(`${item.hidden ? "取消隐藏" : "隐藏"}失败：${(e as Error).message}`);
    return;
  }
  // removing the last card of a page steps back a page instead of
  // refetching into an empty one. The source change on `page` refetches
  // the list on its own; counts need an explicit refresh
  if (items.value.length === 1 && page.value > 0) {
    page.value--;
  } else {
    void refresh();
  }
  void refreshCounts();
}
</script>

<template>
  <div class="grid gap-4 py-4 lg:grid-cols-[180px_1fr]">
    <nav
      class="flex gap-1 self-start overflow-x-auto lg:flex-col lg:overflow-visible"
      aria-label="分类"
    >
      <button
        v-for="item in categoryItems"
        :key="item.value"
        type="button"
        class="flex cursor-pointer items-center gap-2 whitespace-nowrap rounded px-2 py-1.5 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        :class="
          category === item.value
            ? 'bg-accent text-accent-foreground'
            : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
        "
        @click="selectCategory(item.value)"
      >
        <i :class="item.icon" class="size-4 shrink-0" />
        <span>{{ item.label }}</span>
        <span class="ml-auto text-xs tabular-nums">{{ counts[item.value] }}</span>
      </button>
    </nav>

    <div>
      <div class="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <ToggleGroupRoot
          v-if="category !== 'hidden'"
          type="single"
          class="flex items-center gap-1"
          :model-value="kind ?? NULL_KIND"
          @update:model-value="onKindUpdate"
        >
          <ToggleGroupItem
            v-for="opt in kindOptions"
            :key="String(opt.value)"
            :value="opt.value ?? NULL_KIND"
            class="segment-state px-2 py-0.5 text-xs"
          >
            {{ opt.label }}
          </ToggleGroupItem>
        </ToggleGroupRoot>
        <span class="flex items-center gap-1.5">
          <span class="whitespace-nowrap text-xs text-muted-foreground">排序</span>
          <ToggleGroupRoot
            type="single"
            class="flex items-center gap-1"
            :model-value="orderBy"
            @update:model-value="onSortUpdate"
          >
            <ToggleGroupItem
              v-for="opt in sortOptions"
              :key="opt.value"
              :value="opt.value"
              class="segment-state px-2 py-0.5 text-xs"
            >
              {{ opt.label }}
            </ToggleGroupItem>
          </ToggleGroupRoot>
          <Button
            variant="secondary"
            class="px-2"
            :title="direction === 'desc' ? '降序' : '升序'"
            @click="toggleDirection"
          >
            <i
              :class="
                direction === 'desc'
                  ? 'i-lucide-arrow-down-wide-narrow size-4'
                  : 'i-lucide-arrow-up-narrow-wide size-4'
              "
            />
          </Button>
        </span>
        <span class="whitespace-nowrap text-muted-foreground">
          共 {{ total }} 张{{ category === "hidden" ? "（已隐藏）" : "" }}
        </span>
        <span class="ml-auto flex items-center gap-2 whitespace-nowrap">
          <Button variant="secondary" :disabled="page === 0 || loading" @click="page--">
            上一页
          </Button>
          <span>{{ page + 1 }} / {{ pageCount }}</span>
          <Button
            variant="secondary"
            :disabled="(page + 1) * pageSize >= total || loading"
            @click="page++"
          >
            下一页
          </Button>
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
        <div v-for="item in items" :key="item.id" class="group relative">
          <RouterLink
            :to="{ path: `/annotate/${item.id}`, query: annotateQuery }"
            class="block overflow-hidden rounded border border-border bg-card hover:border-ring"
          >
            <div class="relative">
              <img
                v-if="!thumbFailed[item.id]"
                :src="api.thumbUrl(item.id)"
                class="aspect-video w-full object-cover"
                :class="{ grayscale: item.hidden }"
                loading="lazy"
                @error="thumbFailed[item.id] = true"
              />
              <div
                v-else
                class="grid aspect-video w-full place-items-center text-xs text-muted-foreground"
              >
                无缩略图
              </div>
              <!-- literal bg-black/50: opacity utilities silently fail on
                   var()-based semantic tokens -->
              <div
                v-if="item.hidden"
                class="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/50 text-white"
              >
                <i class="i-lucide-eye-off size-6" />
                <span class="text-xs">已隐藏</span>
              </div>
              <div
                v-else-if="isDone(item)"
                class="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/50 text-white"
              >
                <i class="i-lucide-check size-6" />
                <span class="text-xs">{{ item.kind === "b30" ? "B30 已标注" : "已标注" }}</span>
              </div>
              <div
                v-else-if="isDraft(item)"
                class="absolute inset-x-0 bottom-0 flex items-center gap-1.5 bg-warning-soft px-2 py-1 text-xs text-black backdrop-blur-sm"
              >
                <i class="i-lucide-pencil size-3.5" />
                草稿
              </div>
              <div
                v-else-if="b30Progress(item) !== null"
                class="absolute inset-x-0 bottom-0 flex items-center gap-1.5 bg-black/60 px-2 py-1 text-xs text-white backdrop-blur-sm"
              >
                <i class="i-lucide-list-checks size-3.5" />
                标注进度 {{ b30Progress(item) }}
              </div>
            </div>
            <div
              class="flex items-center justify-between gap-1 px-2 py-1 text-xs text-muted-foreground group-hover:text-foreground"
            >
              <span class="truncate">{{ item.original_filename ?? item.id }}</span>
              <span
                v-if="item.kind !== 'device'"
                class="shrink-0 rounded border border-border px-1 text-[10px]"
              >
                {{ item.kind === "b30" ? "B30/50" : "分类未知" }}
              </span>
            </div>
          </RouterLink>
          <button
            type="button"
            class="absolute right-1.5 top-1.5 z-10 grid size-7 cursor-pointer place-items-center rounded bg-black/50 text-white hover:bg-black/70"
            :title="item.hidden ? '取消隐藏' : '隐藏此图'"
            @click="toggleHidden(item)"
          >
            <i :class="item.hidden ? 'i-lucide-eye size-4' : 'i-lucide-eye-off size-4'" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
