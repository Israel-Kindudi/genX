import type { MetadataRoute } from "next";

const baseUrl = "https://genx.vortech.markets";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${baseUrl}/` },
    { url: `${baseUrl}/vision` },
    { url: `${baseUrl}/strategies` },
    { url: `${baseUrl}/research` },
  ];
}
