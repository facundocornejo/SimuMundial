import { FINAL, QF, R16, SF, type KnockoutDefinition, type ResolvedFixture } from "./bracket";
import { MAX_G, koMatrix, matrixSummary } from "./model";
import type { Prode, TeamProfile } from "./types";

export type Random = () => number;

export type DrawnMatch = ResolvedFixture & {
  winner: string;
  score: string;
  p: number;
};

export type KnockoutDraw = {
  r32: DrawnMatch[];
  r16: DrawnMatch[];
  qf: DrawnMatch[];
  sf: DrawnMatch[];
  final: DrawnMatch[];
  champion: string;
};

export function xmur3(input: string) {
  let h = 1779033703 ^ input.length;
  for (let i = 0; i < input.length; i += 1) {
    h = Math.imul(h ^ input.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function seed() {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return (h ^= h >>> 16) >>> 0;
  };
}

export function mulberry32(seed: number): Random {
  return function random() {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function orderedResults(results: Prode["results"]) {
  return Object.fromEntries(
    Object.entries(results).sort(([a], [b]) => a.localeCompare(b)),
  );
}

export function seedFromProde(prode: Prode) {
  return xmur3(`${prode.player}|${JSON.stringify(orderedResults(prode.results))}`)();
}

export function rngFromProde(prode: Prode) {
  return mulberry32(seedFromProde(prode));
}

export function koDraw(
  home: string,
  away: string,
  country: string,
  profiles: Record<string, TeamProfile>,
  rng: Random,
) {
  const { matrix, we } = koMatrix(home, away, country, profiles);
  const { p1, px } = matrixSummary(matrix);
  const homeWinProbability = p1 + px * we;

  const marker = rng();
  let acc = 0;
  let score: [number, number] = [0, 0];
  outer: for (let i = 0; i <= MAX_G; i += 1) {
    for (let j = 0; j <= MAX_G; j += 1) {
      acc += matrix[i][j];
      if (marker <= acc) {
        score = [i, j];
        break outer;
      }
    }
  }

  const penalties = score[0] === score[1];
  const winner = penalties
    ? rng() < we
      ? home
      : away
    : score[0] > score[1]
      ? home
      : away;
  const pwin = winner === home ? homeWinProbability : 1 - homeWinProbability;

  return {
    winner,
    score: `${score[0]}-${score[1]}${penalties ? " (pen)" : ""}`,
    p: Math.round(100 * pwin),
  };
}

function drawRound(
  definitions: KnockoutDefinition[],
  winners: Record<number, string>,
  profiles: Record<string, TeamProfile>,
  rng: Random,
) {
  return definitions.map((definition) => {
    const home = winners[definition.homeFrom];
    const away = winners[definition.awayFrom];
    if (!home || !away) throw new Error(`Missing winners for match ${definition.n}`);
    const drawn = koDraw(home, away, definition.country, profiles, rng);
    winners[definition.n] = drawn.winner;
    return { ...definition, home, away, ...drawn };
  });
}

export function runKnockout(
  r32Fixtures: ResolvedFixture[],
  profiles: Record<string, TeamProfile>,
  rng: Random,
): KnockoutDraw {
  const winners: Record<number, string> = {};
  const r32 = r32Fixtures.map((fixture) => {
    const drawn = koDraw(fixture.home, fixture.away, fixture.country, profiles, rng);
    winners[fixture.n] = drawn.winner;
    return { ...fixture, ...drawn };
  });

  const r16 = drawRound(R16, winners, profiles, rng);
  const qf = drawRound(QF, winners, profiles, rng);
  const sf = drawRound(SF, winners, profiles, rng);
  const final = drawRound([FINAL], winners, profiles, rng);

  return { r32, r16, qf, sf, final, champion: final[0].winner };
}
