import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // The console calls the API at the root, matching how FastAPI serves
    // the built bundle in production. These forward those paths to uvicorn
    // while developing, so there is no dev-only URL shape to get wrong.
    proxy: Object.fromEntries(
      [
        "/health", "/audit", "/schema", "/projects", "/registry",
        "/corpus", "/cannibalization", "/hygiene", "/report",
      ].map((path) => [path, { target: "http://localhost:8000", changeOrigin: true }]),
    ),
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.js"],
  },
});
