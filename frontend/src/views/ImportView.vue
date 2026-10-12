<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { toast } from "vue-sonner";
import { api, type ImportBatch } from "../api";
import Button from "../components/Button.vue";

const sourcePath = ref("");
const recursive = ref(false);
const batches = ref<ImportBatch[]>([]);
const submitting = ref(false);
let timer: ReturnType<typeof setInterval> | undefined;

async function refresh() {
  try {
    batches.value = await api.listImports();
  } catch {
    // transient backend downtime; keep polling
  }
}

function schedule() {
  const running = batches.value.some((b) => b.finished_at == null);
  if (timer) clearInterval(timer);
  timer = setInterval(refresh, running ? 1000 : 5000);
}

async function submit() {
  if (sourcePath.value.trim() === "" || submitting.value) return;
  submitting.value = true;
  try {
    const batch = await api.createImport(sourcePath.value.trim(), recursive.value);
    toast.success(`导入已开始：${batch.id.slice(0, 8)}`);
    await refresh();
    schedule();
  } catch (e) {
    toast.error(`导入失败：${(e as Error).message}`);
  } finally {
    submitting.value = false;
  }
}

onMounted(refresh);
onMounted(schedule);
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="py-4">
    <section class="rounded border border-border bg-card p-4">
      <h2 class="mb-3 text-sm font-semibold">从文件夹导入</h2>
      <!-- label wraps to its own row on mobile; one row again from sm up -->
      <div class="flex flex-wrap items-end gap-3">
        <label class="block w-full sm:w-auto sm:flex-1">
          <span class="field-label">服务器端路径</span>
          <input
            v-model="sourcePath"
            class="field-input mt-0.5"
            placeholder="E:\path\to\screenshots"
            @keyup.enter="submit"
          />
        </label>
        <label class="flex items-center gap-1.5 pb-1.5 text-sm">
          <input v-model="recursive" type="checkbox" />
          含子目录
        </label>
        <Button :disabled="submitting" @click="submit">
          <i
            :class="
              submitting
                ? 'i-lucide-loader-circle size-4 animate-spin'
                : 'i-lucide-folder-plus size-4'
            "
          />
          开始导入
        </Button>
      </div>
    </section>

    <section class="mt-4">
      <h2 class="mb-2 text-sm font-semibold">导入历史</h2>
      <div
        v-for="b in batches"
        :key="b.id"
        class="mb-2 rounded border border-border bg-card p-3 text-sm"
      >
        <div class="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <!-- full path wraps on mobile instead of being ellipsized -->
          <span class="break-all sm:truncate" :title="b.source_path">{{ b.source_path }}</span>
          <span v-if="b.finished_at == null" class="shrink-0 font-medium text-blue-500">
            进行中 {{ b.imported_count + b.skipped_count + b.failed_count }} /
            {{ b.file_count }}
          </span>
          <span v-else class="shrink-0 text-muted-foreground">
            {{ new Date(b.started_at).toLocaleString() }}
          </span>
        </div>
        <div class="mt-1 text-xs text-muted-foreground">
          {{ b.imported_count }} 导入 · {{ b.skipped_count }} 重复跳过 · {{ b.failed_count }} 失败
        </div>
      </div>
    </section>
  </div>
</template>
