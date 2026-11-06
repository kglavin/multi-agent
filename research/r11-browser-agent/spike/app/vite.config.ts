import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build with `vite build app` from spike/. Relative base, so the built app
// works when served from spike/app/dist/.
export default defineConfig({
  base: "./",
  plugins: [react()],
  worker: { format: "es" },
  build: { outDir: "dist", emptyOutDir: true },
});
