import { HomeClient } from "@/components/HomeClient";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "SimuMundial",
  description: "Armá, revelá y compartí tu Mundial pronosticado para 2026.",
};

export default function Home() {
  return <HomeClient />;
}
