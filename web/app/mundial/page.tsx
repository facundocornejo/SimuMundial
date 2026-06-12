import { redirect } from "next/navigation";
import type { Metadata } from "next";
import { MundialGroups } from "@/components/MundialGroups";
import { buildR32 } from "@/lib/bracket";
import { getFixture, getProfiles } from "@/lib/data.server";
import { rngFromProde, runKnockout } from "@/lib/draw";
import { decodeProde } from "@/lib/prode-codec";
import { orderedMatchIds } from "@/lib/match-order";
import { validateProde } from "@/lib/prode-validation";
import type { Prode } from "@/lib/types";

export async function generateMetadata({
  searchParams,
}: {
  searchParams: Promise<{ p?: string }>;
}): Promise<Metadata> {
  const params = await searchParams;
  const title = "Prode Mundial 2026";
  if (!params.p) return { title };

  try {
    const fixture = await getFixture();
    const matchIds = orderedMatchIds(fixture.matches);
    const prode = decodeProde(params.p, matchIds);
    const validation = validateProde(prode, matchIds);
    if (!validation.valid) return { title };
    const ogUrl = `/api/og?p=${encodeURIComponent(params.p)}`;
    return {
      title: `Mundial pronosticado de ${validation.player}`,
      description: "Grupos, cuadro y campeón sorteado desde tu pronóstico del Mundial 2026.",
      openGraph: {
        title: `Mundial pronosticado de ${validation.player}`,
        description: "Grupos, cuadro y campeón sorteado desde tu pronóstico del Mundial 2026.",
        images: [ogUrl],
      },
      twitter: {
        card: "summary_large_image",
        title: `Mundial pronosticado de ${validation.player}`,
        description: "Grupos, cuadro y campeón sorteado desde tu pronóstico del Mundial 2026.",
        images: [ogUrl],
      },
    };
  } catch {
    return { title };
  }
}

export default async function MundialPage({
  searchParams,
}: {
  searchParams: Promise<{ p?: string }>;
}) {
  const params = await searchParams;
  const [fixture, profiles] = await Promise.all([getFixture(), getProfiles()]);
  const matchIds = orderedMatchIds(fixture.matches);
  const code = params.p;
  if (!code) redirect("/prode");

  let prode: Prode;
  try {
    prode = decodeProde(code, matchIds);
  } catch {
    redirect("/prode");
  }

  const validation = validateProde(prode, matchIds);
  if (!validation.valid) redirect("/prode");

  prode = {
    player: validation.player,
    results: prode.results,
  };

  const groups = buildR32(prode.results, fixture.matches, fixture.fairplay);
  const knockout = runKnockout(groups.fixtures, profiles.profiles, rngFromProde(prode));

  return (
    <MundialGroups
      prode={prode}
      matches={fixture.matches}
      ranked={groups.ranked}
      table={groups.table}
      thirds={groups.thirds}
      knockout={knockout}
      prodeCode={code}
    />
  );
}
