import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: "https://genx.vortech.markets/sitemap.xml",
    host: "https://genx.vortech.markets",
  };
}
