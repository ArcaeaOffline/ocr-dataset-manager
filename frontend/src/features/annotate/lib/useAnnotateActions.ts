import { useRouter } from "vue-router";
import { toast } from "vue-sonner";
import type { Ref } from "vue";
import { api, type QueueKind } from "@/api";
import { useBusy } from "@/composables/useBusy";

/**
 * Queue navigation shared by the annotate flows: next-unchecked lookup
 * with its toasts and navigation, hide-and-advance, skip, and one busy
 * slot shared with the caller's own save actions (`T`). `guard` blocks
 * navigation while the current image is still loading - the form then
 * holds the previous image's values.
 */
export function useAnnotateActions<T extends string>(
  imageId: Ref<string>,
  kind: QueueKind,
  guard: () => boolean,
) {
  const router = useRouter();
  const { busyAction, withBusy } = useBusy<T | "skip" | "hide">();

  async function goNext(): Promise<void> {
    let nextId: string | null;
    try {
      ({ id: nextId } = await api.getNextImage(imageId.value, kind));
    } catch (e) {
      toast.error(`获取下一张失败：${(e as Error).message}`);
      return;
    }
    if (nextId === null) {
      toast.success(kind === "b30" ? "没有未标注的 B30 图片了" : "没有未标注的图片了");
      await router.push("/");
      return;
    }
    await router.replace(`/annotate/${nextId}`);
  }

  async function hideAndNext(): Promise<void> {
    if (guard()) return;
    await withBusy("hide", async () => {
      try {
        await api.setImageHidden(imageId.value, true);
      } catch (e) {
        toast.error(`隐藏失败：${(e as Error).message}`);
        return;
      }
      await goNext();
    });
  }

  async function skip(): Promise<void> {
    if (guard()) return;
    await withBusy("skip", goNext);
  }

  return { busyAction, withBusy, goNext, skip, hideAndNext };
}
