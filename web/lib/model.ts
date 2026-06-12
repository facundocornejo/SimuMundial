import type { TeamProfile } from "./types";

export const HOME_ADV = 85;
export const RHO = 1.1;
export const MAX_G = 8;
export const MIN_LAMBDA = 0.18;
export const BASE_TOTAL = 2.55;

export function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export function eloWe(diff: number) {
  return 1 / (1 + 10 ** (-diff / 400));
}

export function poissonPmf(lambda: number, k: number) {
  let factorial = 1;
  for (let i = 2; i <= k; i += 1) factorial *= i;
  return (Math.exp(-lambda) * lambda ** k) / factorial;
}

export function lambdas(home: TeamProfile, away: TeamProfile, venueCountry?: string, homeTeam?: string, awayTeam?: string) {
  const diff =
    home.elo -
    away.elo +
    (homeTeam && homeTeam === venueCountry ? HOME_ADV : 0) -
    (awayTeam && awayTeam === venueCountry ? HOME_ADV : 0);
  const we = eloWe(diff);
  const attack =
    (home.avg_gf_2y + away.avg_gc_2y + away.avg_gf_2y + home.avg_gc_2y) / 2;
  const total = clamp(0.5 * BASE_TOTAL + 0.5 * attack, 1.8, 3.6);
  return {
    lambdaHome: Math.max(MIN_LAMBDA, total * we),
    lambdaAway: Math.max(MIN_LAMBDA, total * (1 - we)),
    diff,
    we,
  };
}

export function buildMatrix(lambdaHome: number, lambdaAway: number, rho = RHO, maxGoals = MAX_G) {
  const home = Array.from({ length: maxGoals + 1 }, (_, i) => poissonPmf(lambdaHome, i));
  const away = Array.from({ length: maxGoals + 1 }, (_, i) => poissonPmf(lambdaAway, i));
  const matrix = home.map((homeP, i) =>
    away.map((awayP, j) => homeP * awayP * (i === j ? rho : 1)),
  );
  const total = matrix.flat().reduce((sum, value) => sum + value, 0);
  return matrix.map((row) => row.map((value) => value / total));
}

export function matrixSummary(matrix: number[][]) {
  let p1 = 0;
  let px = 0;
  let best: [number, number] = [0, 0];
  let bestValue = -1;
  let over25 = 0;

  for (let i = 0; i < matrix.length; i += 1) {
    for (let j = 0; j < matrix[i].length; j += 1) {
      const value = matrix[i][j];
      if (i > j) p1 += value;
      if (i === j) px += value;
      if (i + j >= 3) over25 += value;
      if (value > bestValue) {
        best = [i, j];
        bestValue = value;
      }
    }
  }

  return { p1, px, p2: 1 - p1 - px, best, over25 };
}

export function koMatrix(
  homeTeam: string,
  awayTeam: string,
  venueCountry: string,
  profiles: Record<string, TeamProfile>,
) {
  const values = lambdas(
    profiles[homeTeam],
    profiles[awayTeam],
    venueCountry,
    homeTeam,
    awayTeam,
  );
  return { matrix: buildMatrix(values.lambdaHome, values.lambdaAway), we: values.we };
}
