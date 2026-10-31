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
      background: "var(--background)",
      foreground: "var(--foreground)",
      card: { DEFAULT: "var(--card)", foreground: "var(--card-foreground)" },
      popover: {
        DEFAULT: "var(--popover)",
        foreground: "var(--popover-foreground)",
      },
      primary: {
        DEFAULT: "var(--primary)",
        foreground: "var(--primary-foreground)",
      },
      secondary: {
        DEFAULT: "var(--secondary)",
        foreground: "var(--secondary-foreground)",
      },
      muted: { DEFAULT: "var(--muted)", foreground: "var(--muted-foreground)" },
      accent: { DEFAULT: "var(--accent)", foreground: "var(--accent-foreground)" },
      destructive: {
        DEFAULT: "var(--destructive)",
        foreground: "var(--destructive-foreground)",
        soft: "var(--destructive-soft)",
        border: "var(--destructive-border)",
      },
      warning: { DEFAULT: "var(--warning)", soft: "var(--warning-soft)" },
      info: "var(--info)",
      border: "var(--border)",
      input: "var(--input)",
      ring: "var(--ring)",
    },
  },
  shortcuts: {
    "field-input":
      "w-full rounded border border-input bg-background px-2 py-1 text-sm text-foreground outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
    "field-label": "text-xs text-muted-foreground",
    btn: "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium bg-primary text-primary-foreground hover:opacity-80 disabled:opacity-50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    "btn-secondary":
      "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium bg-secondary text-secondary-foreground border border-border hover:opacity-80 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    "btn-destructive":
      "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded px-3 py-1.5 text-sm font-medium bg-destructive text-destructive-foreground hover:opacity-80 disabled:opacity-50 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    "btn-ghost":
      "grid size-8 shrink-0 cursor-pointer place-items-center rounded text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    "btn-ghost-dark":
      "grid size-8 shrink-0 cursor-pointer place-items-center rounded text-white hover:bg-white/10 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    "segment-state":
      "cursor-pointer rounded border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[state=off]:border-border data-[state=off]:bg-secondary data-[state=off]:text-secondary-foreground data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground",
    "combobox-item":
      "flex cursor-pointer items-center gap-2 px-2 py-1.5 text-left text-sm data-[highlighted]:bg-accent",
  },
});
