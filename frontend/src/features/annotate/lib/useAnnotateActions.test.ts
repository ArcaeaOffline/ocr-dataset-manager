import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useAnnotateActions } from "./useAnnotateActions";

const { replace, push, getNextImage, getPrevImage, croppedUrl, toastError, toastSuccess, state } =
  vi.hoisted(() => ({
    replace: vi.fn(),
    push: vi.fn(),
    getNextImage: vi.fn(),
    getPrevImage: vi.fn(),
    croppedUrl: vi.fn((id: string) => `${id}-cropped`),
    toastError: vi.fn(),
    toastSuccess: vi.fn(),
    state: { query: {} as Record<string, unknown> },
  }));

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: state.query }),
  useRouter: () => ({ replace, push }),
}));

vi.mock("@/api", () => ({
  api: { getNextImage, getPrevImage, setImageHidden: vi.fn(), croppedUrl },
}));

vi.mock("vue-sonner", () => ({
  toast: { error: toastError, success: toastSuccess },
}));

// the preload warms the browser cache through the DOM Image constructor,
// which a node environment lacks
vi.stubGlobal(
  "Image",
  class {
    src = "";
  },
);

function setup(flow: "device" | "b30" = "device") {
  return useAnnotateActions<"save">(ref("cur"), flow, () => false);
}

beforeEach(() => {
  vi.clearAllMocks();
  state.query = {};
});

describe("useAnnotateActions", () => {
  it("forwards the queue traversal to the api call and the next hop", async () => {
    state.query = { category: "all", order_by: "original_filename", direction: "asc" };
    getNextImage.mockResolvedValue({ id: "n2" });

    await setup().goNext();

    expect(getNextImage).toHaveBeenCalledWith("cur", "device", {
      category: "all",
      order_by: "original_filename",
      direction: "asc",
    });
    expect(replace).toHaveBeenCalledWith({ path: "/annotate/n2", query: state.query });
  });

  it("walks backwards carrying the same traversal", async () => {
    state.query = { category: "checked" };
    getPrevImage.mockResolvedValue({ id: "p1" });

    await setup().goPrev();

    expect(getPrevImage).toHaveBeenCalledWith("cur", "device", { category: "checked" });
    expect(replace).toHaveBeenCalledWith({ path: "/annotate/p1", query: state.query });
  });

  it("a bare entry walks the endpoint defaults with an empty query", async () => {
    getNextImage.mockResolvedValue({ id: "n1" });

    await setup().goNext();

    expect(getNextImage).toHaveBeenCalledWith("cur", "device", {});
    expect(replace).toHaveBeenCalledWith({ path: "/annotate/n1", query: {} });
  });

  it("exhaustion goes home and names the walked slice", async () => {
    state.query = { category: "all" };
    getNextImage.mockResolvedValue({ id: null });

    await setup().goNext();

    expect(toastSuccess).toHaveBeenCalledWith("没有更多图片了");
    expect(push).toHaveBeenCalledWith("/");
    expect(replace).not.toHaveBeenCalled();
  });

  it("an exhausted unchecked slice keeps the flow-specific message", async () => {
    getNextImage.mockResolvedValue({ id: null });

    await setup("b30").goNext();

    expect(toastSuccess).toHaveBeenCalledWith("没有未标注的 B30 图片了");
  });

  it("an api failure toasts instead of navigating", async () => {
    getNextImage.mockRejectedValue(new Error("boom"));

    await setup().goNext();

    expect(toastError).toHaveBeenCalledWith("获取下一张失败：boom");
    expect(replace).not.toHaveBeenCalled();
  });

  it("preload warms the next image and survives failure and exhaustion", async () => {
    getNextImage.mockResolvedValue({ id: "n2" });
    await setup().preloadNext();
    expect(getNextImage).toHaveBeenCalledWith("cur", "device", {});
    expect(croppedUrl).toHaveBeenCalledWith("n2");

    // the current image itself needs no warm-up
    getNextImage.mockResolvedValue({ id: "cur" });
    await setup().preloadNext();
    expect(croppedUrl).toHaveBeenCalledTimes(1);

    getNextImage.mockResolvedValue({ id: null });
    await expect(setup().preloadNext()).resolves.toBeUndefined();
    getNextImage.mockRejectedValue(new Error("down"));
    await expect(setup().preloadNext()).resolves.toBeUndefined();
  });
});
