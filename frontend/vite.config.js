import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" lets the built files work when the backend serves them under /ui/
export default defineConfig({
  base: "./",
  plugins: [react()],
  server: { port: 5173, host: "127.0.0.1" },
  build: { outDir: "dist", emptyOutDir: true },
});
