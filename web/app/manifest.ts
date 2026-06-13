import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "SimuMundial",
    short_name: "SimuMundial",
    description: "Carga, revela y comparte tu Mundial 2026 simulado.",
    start_url: "/",
    display: "standalone",
    background_color: "#050911",
    theme_color: "#e7b84b",
    lang: "es-AR",
  };
}
