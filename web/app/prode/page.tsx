import { ProdeBuilder } from "@/components/ProdeBuilder";
import { getFixture, getModelPicks, getPredictions } from "@/lib/data.server";
import { orderedMatchIds } from "@/lib/match-order";
import { decodeProde } from "@/lib/prode-codec";
import { validateProde } from "@/lib/prode-validation";
import type { Metadata } from "next";
import type { Prode } from "@/lib/types";

export const metadata: Metadata = {
  title: "Cargar prode | Prode Mundial 2026",
  description: "Cargá, editá o completá tu pronóstico de los 72 partidos de grupos del Mundial 2026.",
};

export default async function ProdePage({
  searchParams,
}: {
  searchParams: Promise<{ new?: string; p?: string }>;
}) {
  const params = await searchParams;
  const [fixture, predictions, modelPicks] = await Promise.all([
    getFixture(),
    getPredictions(),
    getModelPicks(),
  ]);
  const matchIds = orderedMatchIds(fixture.matches);
  let initialProde: Prode | null = null;

  if (params.p) {
    try {
      const decoded = decodeProde(params.p, matchIds);
      const validation = validateProde(decoded, matchIds);
      if (validation.valid) {
        initialProde = {
          player: validation.player,
          results: decoded.results,
        };
      }
    } catch {}
  }

  return (
    <ProdeBuilder
      matches={fixture.matches}
      predictions={predictions.predictions}
      modelPicks={modelPicks}
      initialProde={initialProde}
      forceNew={params.new === "1"}
    />
  );
}
