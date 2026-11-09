import { fileURLToPath, URL } from "node:url";

import UnoCSS from "unocss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue(), UnoCSS()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 8190,
    proxy: {
      "/api": "http://127.0.0.1:8199",
    },
  },
});
