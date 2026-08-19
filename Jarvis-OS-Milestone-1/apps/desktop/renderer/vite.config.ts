import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

// Resolve sempre em relação à pasta deste arquivo, não ao cwd de onde o comando é chamado
const rendererDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  root: rendererDir,
  build: {
    outDir: path.resolve(rendererDir, "dist"),
    emptyOutDir: true
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true
  }
});