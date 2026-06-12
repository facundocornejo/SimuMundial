import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Prode Mundial 2026",
    short_name: "Prode 2026",
    description: "Carga, revela y comparte tu pronostico del Mundial 2026.",
    start_url: "/",
    display: "standalone",
    background_color: "#080d16",
    theme_color: "#e7b84b",
    lang: "es-AR",
  };
}
