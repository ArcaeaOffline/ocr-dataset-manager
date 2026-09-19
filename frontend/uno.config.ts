import { defineConfig, presetIcons, presetWind3 } from "unocss";

// semantic color tokens in the shadcn convention, resolved from CSS
// variables declared in src/style.css (light + dark)
export default defineConfig({
  presets: [
    presetWind3(),
    presetIcons({
      extraProperties: { display: "inline-block", "vertical-align": "middle" },
    }),
  ],
  theme: {
    colors: {
      background: "var(--bg)",
      foreground: "var(--fg)",
      card: "var(--card)",
      primary: {
        DEFAULT: "var(--primary)",
        fg: "var(--primary-fg)",
      },
      secondary: {
        DEFAULT: "var(--secondary)",
        fg: "var(--secondary-fg)",
      },
      muted: { DEFAULT: "var(--muted)", foreground: "var(--muted-fg)" },
      destructive: {
        DEFAULT: "var(--destructive)",
        fg: "var(--destructive-fg)",
      },
      border: "var(--border)",
      input: "var(--input)",
      ring: "var(--ring)",
    },
  },
  shortcuts: {
    "field-input":
      "w-full rounded border border-input bg-background px-2 py-1 text-sm text-foreground outline-none focus:border-ring",
    "field-label": "text-xs text-muted-foreground",
    btn: "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium bg-primary text-primary-fg disabled:opacity-50 cursor-pointer",
    "btn-secondary":
      "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium bg-secondary text-secondary-fg border border-border cursor-pointer",
  },
});
