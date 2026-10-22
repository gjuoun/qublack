import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  const origin = site ? new URL(site).origin : "https://qublack.qqntt.com";
  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>${origin}/</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>
</urlset>
`;
  return new Response(body, { headers: { "Content-Type": "application/xml" } });
};
