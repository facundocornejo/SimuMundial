import { GROUP_CODES, GROUPS } from "./teams";
import type { Match, Score } from "./types";

export type TeamStats = {
  pts: number;
  gf: number;
  gc: number;
};

export type StandingsResult = {
  ranked: Record<string, string[]>;
  table: Record<string, TeamStats>;
};

export function emptyTable(): Record<string, TeamStats> {
  return Object.fromEntries(
    GROUP_CODES.flatMap((group) =>
      GROUPS[group].map((team) => [team, { pts: 0, gf: 0, gc: 0 }]),
    ),
  );
}

export function rankKey(
  team: string,
  table: Record<string, TeamStats>,
  fairplay: Record<string, number> = {},
) {
  const stats = table[team];
  return [
    -stats.pts,
    -(stats.gf - stats.gc),
    -stats.gf,
    -fairplay[team] || 0,
    team,
  ] as const;
}

export function compareTeams(
  a: string,
  b: string,
  table: Record<string, TeamStats>,
  fairplay: Record<string, number> = {},
) {
  const ak = rankKey(a, table, fairplay);
  const bk = rankKey(b, table, fairplay);
  for (let i = 0; i < ak.length; i += 1) {
    if (ak[i] < bk[i]) return -1;
    if (ak[i] > bk[i]) return 1;
  }
  return 0;
}

export function computeStandings(
  results: Record<string, Score>,
  matches: Match[],
  fairplay: Record<string, number> = {},
): StandingsResult {
  const table = emptyTable();

  for (const match of matches) {
    const score = results[match.match_id];
    if (!score) continue;

    const [homeScore, awayScore] = score;
    const home = table[match.home];
    const away = table[match.away];
    if (!home || !away) continue;

    home.gf += homeScore;
    home.gc += awayScore;
    away.gf += awayScore;
    away.gc += homeScore;

    if (homeScore > awayScore) home.pts += 3;
    else if (homeScore < awayScore) away.pts += 3;
    else {
      home.pts += 1;
      away.pts += 1;
    }
  }

  const ranked = Object.fromEntries(
    GROUP_CODES.map((group) => [
      group,
      [...GROUPS[group]].sort((a, b) => compareTeams(a, b, table, fairplay)),
    ]),
  );

  return { ranked, table };
}

export function bestThirds(
  ranked: Record<string, string[]>,
  table: Record<string, TeamStats>,
  fairplay: Record<string, number> = {},
) {
  return GROUP_CODES.map((group) => ranked[group][2])
    .filter(Boolean)
    .sort((a, b) => compareTeams(a, b, table, fairplay))
    .slice(0, 8);
}
