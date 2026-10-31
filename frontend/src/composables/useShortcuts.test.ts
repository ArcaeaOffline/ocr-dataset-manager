import { describe, expect, it } from "vitest";
import { matchShortcut, type ShortcutBinding } from "./useShortcuts";

function event(key: string, ctrlKey = false, altKey = false, metaKey = false) {
  return { key, ctrlKey, metaKey, altKey };
}

const bindings: ShortcutBinding[] = [
  { key: "enter", ctrl: true, handler: () => {} },
  { key: "s", ctrl: true, handler: () => {} },
  { key: "s", handler: () => {} },
  { key: "arrowleft", handler: () => {} },
];

describe("matchShortcut", () => {
  it("matches the key and requires modifiers to match exactly", () => {
    expect(matchShortcut(event("Enter", true), bindings)?.key).toBe("enter");
    expect(matchShortcut(event("s", true), bindings)?.key).toBe("s");
    expect(matchShortcut(event("s"), bindings)?.key).toBe("s");
    // ctrl+s never reaches the plain-s binding
    expect(matchShortcut(event("s", true), bindings)).not.toBe(bindings[2]);
    expect(matchShortcut(event("s"), bindings)).not.toBe(bindings[1]);
  });

  it("matches keys case-insensitively", () => {
    expect(matchShortcut(event("ArrowLeft"), bindings)?.key).toBe("arrowleft");
    expect(matchShortcut(event("S"), bindings)?.key).toBe("s");
  });

  it("rejects unexpected modifiers", () => {
    expect(matchShortcut(event("s", false, true), bindings)).toBeNull();
    expect(matchShortcut(event("s", true, true), bindings)).toBeNull();
  });

  it("treats Cmd (metaKey) as the ctrl modifier for macOS", () => {
    // Cmd+S must save, not fall through to the plain-s binding
    const cmdS = matchShortcut(event("s", false, false, true), bindings);
    expect(cmdS).toBe(bindings[1]);
    expect(cmdS).not.toBe(bindings[2]);
    expect(matchShortcut(event("Enter", false, false, true), bindings)?.key).toBe("enter");
  });

  it("returns null when nothing matches", () => {
    expect(matchShortcut(event("x"), bindings)).toBeNull();
    expect(matchShortcut(event("Enter"), bindings)).toBeNull();
  });
});
