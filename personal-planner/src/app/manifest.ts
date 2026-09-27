import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "나의 플래너",
    short_name: "플래너",
    description: "할일·일정·습관을 한 곳에서 관리하는 개인용 플래너",
    start_url: "/",
    display: "standalone",
    background_color: "#f6f7f9",
    theme_color: "#6366f1",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
      },
    ],
  };
}
