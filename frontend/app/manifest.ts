import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "RPL-Sahayak AI",
    short_name: "RPL-Sahayak",
    description: "AI-assisted prior learning assessment support (SIH26242 prototype). Works offline in the field.",
    start_url: "/worker/dashboard",
    display: "standalone",
    background_color: "#f5f3ee",
    theme_color: "#16191d",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
