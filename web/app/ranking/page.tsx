import Link from "next/link";
import type { Metadata } from "next";
import { buildR32 } from "@/lib/bracket";
import { getFixture, getModelPicks, getProfiles, getStoredProdes } from "@/lib/data.server";
import { rngFromProde, runKnockout } from "@/lib/draw";
import { orderedMatchIds } from "@/lib/match-order";
import { encodeProde } from "@/lib/prode-codec";
import { scoreProde } from "@/lib/scoring";
import type { Prode } from "@/lib/types";

export const metadata: Metadata = {
  title: "Ranking | Prode Mundial 2026",
  description: "Tabla de puntajes del prode contra los resultados reales ya jugados.",
};

function championFor(prode: Prode, fixture: Awaited<ReturnType<typeof getFixture>>, profiles: Awaited<ReturnType<typeof getProfiles>>) {
  const r32 = buildR32(prode.results, fixture.matches, fixture.fairplay).fixtures;
  return runKnockout(r32, profiles.profiles, rngFromProde(prode)).champion;
}

export default async function RankingPage() {
  const [fixture, profiles, prodes, modelPicks] = await Promise.all([
    getFixture(),
    getProfiles(),
    getStoredProdes(),
    getModelPicks(),
  ]);
  const matchIds = orderedMatchIds(fixture.matches);
  const players: Prode[] = [
    ...prodes,
    { player: "🤖 Modelo", results: modelPicks },
  ];

  const rows = players
    .map((prode) => {
      const score = scoreProde(prode, fixture.matches);
      const champion = championFor(prode, fixture, profiles);
      return {
        player: prode.player,
        exact: score.exact,
        outcome: score.outcome,
        points: score.points,
        champion,
        code: encodeProde(prode, matchIds),
      };
    })
    .sort((a, b) => b.points - a.points || b.exact - a.exact || a.player.localeCompare(b.player));

  return (
    <main className="ranking-shell">
      <header className="ranking-header">
        <div>
          <p className="eyebrow">Ranking</p>
          <h1>Tabla del prode</h1>
        </div>
        <Link className="button button--primary" href="/prode">
          Cargar otro
        </Link>
      </header>

      <section className="ranking-table" aria-label="Ranking de jugadores">
        <div className="ranking-row ranking-row--head">
          <span>#</span>
          <span>Nombre</span>
          <span>Exactos</span>
          <span>1X2</span>
          <span>Puntos</span>
          <span>Campeón</span>
          <span>Link</span>
        </div>
        {rows.map((row, index) => (
          <div className="ranking-row" key={`${row.player}-${row.code}`}>
            <span>{index + 1}</span>
            <strong>{row.player}</strong>
            <span>{row.exact}</span>
            <span>{row.outcome}</span>
            <strong>{row.points}</strong>
            <span>{row.champion}</span>
            <Link href={`/mundial?p=${row.code}`}>Ver</Link>
          </div>
        ))}
      </section>
    </main>
  );
}
