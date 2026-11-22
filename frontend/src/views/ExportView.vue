<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { toast } from "vue-sonner";
import { api, type ExportJob } from "@/api";
import Button from "@/components/ui/Button.vue";
import ConfirmDialog from "@/components/ui/ConfirmDialog.vue";

const exports = ref<ExportJob[]>([]);
const submitting = ref(false);
// non-null opens the delete confirmation
const deleting = ref<ExportJob | null>(null);
let timer: ReturnType<typeof setInterval> | undefined;

async function refresh() {
  try {
    exports.value = await api.listExports();
  } catch {
    // transient backend downtime. Keep polling
  } finally {
    // interval decided from the freshest list, so a running export
    // found at mount time switches to the 1s interval immediately
    schedule();
  }
}

function schedule() {
  const running = exports.value.some((e) => e.finished_at == null);
  if (timer) clearInterval(timer);
  timer = setInterval(refresh, running ? 1000 : 5000);
}

async function submit() {
  if (submitting.value) return;
  submitting.value = true;
  try {
    const job = await api.createExport();
    toast.success(`导出已开始：${job.name.slice(0, 15)}`);
    await refresh();
  } catch (e) {
    toast.error(`导出失败：${(e as Error).message}`);
  } finally {
    submitting.value = false;
  }
}

async function remove() {
  if (!deleting.value) return;
  try {
    await api.deleteExport(deleting.value.id);
    toast.success("导出已删除");
    deleting.value = null;
    await refresh();
  } catch (e) {
    toast.error(`删除失败：${(e as Error).message}`);
  }
}

onMounted(refresh);
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>

<template>
  <div class="py-4">
    <section class="rounded border border-border bg-card p-4">
      <h2 class="mb-3 text-sm font-semibold">导出训练数据</h2>
      <div class="flex flex-wrap items-end gap-3">
        <Button :disabled="submitting" @click="submit">
          <i
            :class="
              submitting ? 'i-lucide-loader-circle size-4 animate-spin' : 'i-lucide-download size-4'
            "
          />
          开始导出
        </Button>
      </div>
    </section>

    <section class="mt-4">
      <h2 class="mb-2 text-sm font-semibold">导出历史</h2>
      <div
        v-for="e in exports"
        :key="e.id"
        class="mb-2 rounded border border-border bg-card p-3 text-sm"
      >
        <div class="flex flex-col gap-0.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <span class="break-all font-mono text-xs">{{ e.name }}</span>
          <span v-if="e.finished_at == null" class="shrink-0 font-medium text-info">
            进行中 {{ e.exported_count + e.skipped_count + e.failed_count }} /
            {{ e.file_count }}
          </span>
          <span v-else class="shrink-0 text-muted-foreground">
            {{ new Date(e.started_at).toLocaleString() }}
          </span>
        </div>
        <div class="mt-1 text-xs text-muted-foreground">
          {{ e.exported_count }} 导出 · {{ e.skipped_count }} 跳过 · {{ e.failed_count }} 失败
        </div>
        <div v-if="e.error" class="mt-1 break-all text-xs text-destructive">
          {{ e.error }}
        </div>
        <div v-if="e.finished_at != null" class="mt-2 flex gap-2">
          <a
            v-if="e.error == null"
            class="btn-secondary"
            :href="api.exportDownloadUrl(e.id)"
            download
          >
            <i class="i-lucide-download size-4" />
            下载
          </a>
          <button type="button" class="btn-ghost" @click="deleting = e">
            <i class="i-lucide-trash-2 size-4" />
            删除
          </button>
        </div>
      </div>
    </section>

    <ConfirmDialog
      :open="deleting != null"
      title="删除导出"
      :description="`删除该次导出的记录、数据目录与 zip 归档？\n${deleting?.name}`"
      confirm-label="删除"
      destructive
      @update:open="(value) => !value && (deleting = null)"
      @confirm="remove"
    />
  </div>
</template>
