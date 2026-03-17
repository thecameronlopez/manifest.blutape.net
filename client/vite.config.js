import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, new URL(".", import.meta.url).pathname, "");
  const resolvedServerUrl = (
    env.VITE_SERVER_URL ||
    process.env.VITE_SERVER_URL ||
    "http://127.0.0.1:8000"
  ).replace(/^['"]|['"]$/g, "");

  return {
    plugins: [
      react({
        babel: {
          plugins: [["babel-plugin-react-compiler"]],
        },
      }),
    ],
    server: {
      proxy: {
      "/api": {
          target: resolvedServerUrl,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
