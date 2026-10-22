import react from "@astrojs/react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "astro/config";

// One deployment: Cloudflare Pages, served from the root of https://qublack.qqntt.com/
export default defineConfig({
  site: "https://qublack.qqntt.com",
  trailingSlash: "always",
  build: { format: "directory" },
  integrations: [react()],
  vite: { plugins: [tailwindcss()] },
});
