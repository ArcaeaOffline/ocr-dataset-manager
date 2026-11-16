import { useRouter } from "vue-router";
import { toast } from "vue-sonner";
import type { Ref } from "vue";

import { api } from "@/api";
import { useBusy } from "@/composables/useBusy";
import { useQueueTraversal } from "./queueContext";

/**
 * Queue navigation shared by the annotate flows: adjacent-image lookup
 * with its toasts and navigation, hide-and-advance, skip, one step
 * back, and the next-image preload. One busy slot is shared with the
 * caller's own save actions (`T`). `guard` blocks navigation while the
 * current image is still loading - the form then holds the previous
 * image's values. The walk follows the queue view's traversal context
 * (route query): the category slice and ordering ride along to /next
 * and /prev.
 */
export function useAnnotateActions<T extends string>(
  imageId: Ref<string>,
  flow: "device" | "b30",
  guard: () => boolean,
) {
  const router = useRouter();
  const { traversal, annotateLocation } = useQueueTraversal();
  const { busyAction, withBusy } = useBusy<T | "skip" | "hide" | "prev">();

  // the exhausted message names the slice being walked, since only the
  // unchecked slice is about annotation progress
  function exhaustedToast(): string {
    const { category } = traversal.value;
    if (category === "all" || category === "checked") return "没有更多图片了";
    return flow === "b30" ? "没有未标注的 B30 图片了" : "没有未标注的图片了";
  }

  async function navigate(
    apiCall: () => Promise<{ id: string | null }>,
    failureLabel: string,
  ): Promise<void> {
    let nextId: string | null;
    try {
      ({ id: nextId } = await apiCall());
    } catch (e) {
      toast.error(`获取${failureLabel}失败：${(e as Error).message}`);
      return;
    }
    if (nextId === null) {
      toast.success(exhaustedToast());
      await router.push("/");
      return;
    }
    await router.replace(annotateLocation(nextId));
  }

  /** Best-effort preload of the next image's cropped copy; never
   * throws. */
  async function preloadNext() {
    try {
      const { id: nextId } = await api.getNextImage(imageId.value, flow, traversal.value);
      if (nextId != null && nextId !== imageId.value) {
        new Image().src = api.croppedUrl(nextId);
      }
    } catch {
      // best-effort
    }
  }

  /** Bare forward navigation, also used after saving. */
  async function goNext(): Promise<void> {
    await navigate(() => api.getNextImage(imageId.value, flow, traversal.value), "下一张");
  }

  /** One guarded, busy-tracked step backwards through the same walk. */
  async function goPrev(): Promise<void> {
    if (guard()) return;
    await withBusy("prev", () =>
      navigate(() => api.getPrevImage(imageId.value, flow, traversal.value), "上一张"),
    );
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

  return { busyAction, withBusy, goNext, goPrev, skip, hideAndNext, preloadNext };
}
