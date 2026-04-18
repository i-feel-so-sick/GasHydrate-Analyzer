import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [react()],
    server: {
      port: Number(env.VITE_DEV_PORT || 5173),
      host: env.VITE_DEV_HOST || "0.0.0.0",
      proxy: {
        "/api": env.VITE_BACKEND_URL || "http://localhost:8000",
      },
    },
  };
});
