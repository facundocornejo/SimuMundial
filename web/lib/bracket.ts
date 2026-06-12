import { GROUP_CODES, GROUPS, TEAM_GROUP } from "./teams";
import type { Match, Score } from "./types";
import { bestThirds, computeStandings } from "./standings";

type Slot = ["W" | "R", string] | ["T", string];

export type R32Definition = {
  n: number;
  homeSlot: Slot;
  awaySlot: Slot;
  date: string;
  venue: string;
  country: string;
};

export type KnockoutDefinition = {
  n: number;
  homeFrom: number;
  awayFrom: number;
  date: string;
  venue: string;
  country: string;
};

export type ResolvedFixture = {
  n: number;
  home: string;
  away: string;
  date: string;
  venue: string;
  country: string;
};

export const R32: R32Definition[] = [
  { n: 73, homeSlot: ["R", "A"], awaySlot: ["R", "B"], date: "28/6", venue: "SoFi Stadium, Inglewood", country: "United States" },
  { n: 74, homeSlot: ["W", "E"], awaySlot: ["T", "ABCDF"], date: "29/6", venue: "Gillette Stadium, Boston", country: "United States" },
  { n: 75, homeSlot: ["W", "F"], awaySlot: ["R", "C"], date: "29/6", venue: "Estadio BBVA, Monterrey", country: "Mexico" },
  { n: 76, homeSlot: ["W", "C"], awaySlot: ["R", "F"], date: "29/6", venue: "NRG Stadium, Houston", country: "United States" },
  { n: 77, homeSlot: ["W", "I"], awaySlot: ["T", "CDFGH"], date: "30/6", venue: "MetLife Stadium, NY/NJ", country: "United States" },
  { n: 78, homeSlot: ["R", "E"], awaySlot: ["R", "I"], date: "30/6", venue: "AT&T Stadium, Dallas", country: "United States" },
  { n: 79, homeSlot: ["W", "A"], awaySlot: ["T", "CEFHI"], date: "30/6", venue: "Estadio Azteca, CDMX", country: "Mexico" },
  { n: 80, homeSlot: ["W", "L"], awaySlot: ["T", "EHIJK"], date: "1/7", venue: "Mercedes-Benz, Atlanta", country: "United States" },
  { n: 81, homeSlot: ["W", "D"], awaySlot: ["T", "BEFIJ"], date: "1/7", venue: "Levi's Stadium, Santa Clara", country: "United States" },
  { n: 82, homeSlot: ["W", "G"], awaySlot: ["T", "AEHIJ"], date: "1/7", venue: "Lumen Field, Seattle", country: "United States" },
  { n: 83, homeSlot: ["R", "K"], awaySlot: ["R", "L"], date: "2/7", venue: "BMO Field, Toronto", country: "Canada" },
  { n: 84, homeSlot: ["W", "H"], awaySlot: ["R", "J"], date: "2/7", venue: "SoFi Stadium, Inglewood", country: "United States" },
  { n: 85, homeSlot: ["W", "B"], awaySlot: ["T", "EFGIJ"], date: "2/7", venue: "BC Place, Vancouver", country: "Canada" },
  { n: 86, homeSlot: ["W", "J"], awaySlot: ["R", "H"], date: "3/7", venue: "Hard Rock, Miami", country: "United States" },
  { n: 87, homeSlot: ["W", "K"], awaySlot: ["T", "DEIJL"], date: "3/7", venue: "Arrowhead, Kansas City", country: "United States" },
  { n: 88, homeSlot: ["R", "D"], awaySlot: ["R", "G"], date: "3/7", venue: "AT&T Stadium, Dallas", country: "United States" },
];

export const R16: KnockoutDefinition[] = [
  { n: 89, homeFrom: 74, awayFrom: 77, date: "4/7", venue: "Philadelphia", country: "United States" },
  { n: 90, homeFrom: 73, awayFrom: 75, date: "4/7", venue: "Houston", country: "United States" },
  { n: 91, homeFrom: 76, awayFrom: 78, date: "5/7", venue: "Estadio Azteca, CDMX", country: "Mexico" },
  { n: 92, homeFrom: 79, awayFrom: 80, date: "5/7", venue: "Dallas", country: "United States" },
  { n: 93, homeFrom: 83, awayFrom: 84, date: "6/7", venue: "Seattle", country: "United States" },
  { n: 94, homeFrom: 81, awayFrom: 82, date: "6/7", venue: "Atlanta", country: "United States" },
  { n: 95, homeFrom: 86, awayFrom: 88, date: "7/7", venue: "Vancouver", country: "Canada" },
  { n: 96, homeFrom: 85, awayFrom: 87, date: "7/7", venue: "Miami", country: "United States" },
];

export const QF: KnockoutDefinition[] = [
  { n: 97, homeFrom: 89, awayFrom: 90, date: "9/7", venue: "Boston", country: "United States" },
  { n: 98, homeFrom: 93, awayFrom: 94, date: "10/7", venue: "Los Ángeles", country: "United States" },
  { n: 99, homeFrom: 91, awayFrom: 92, date: "11/7", venue: "Miami", country: "United States" },
  { n: 100, homeFrom: 95, awayFrom: 96, date: "11/7", venue: "Kansas City", country: "United States" },
];

export const SF: KnockoutDefinition[] = [
  { n: 101, homeFrom: 97, awayFrom: 98, date: "14/7", venue: "Dallas", country: "United States" },
  { n: 102, homeFrom: 99, awayFrom: 100, date: "15/7", venue: "Atlanta", country: "United States" },
];

export const FINAL: KnockoutDefinition = {
  n: 104,
  homeFrom: 101,
  awayFrom: 102,
  date: "19/7",
  venue: "MetLife Stadium, NY/NJ",
  country: "United States",
};

export function assignThirds(qualifiedGroups: string[]) {
  const groupSet = new Set(qualifiedGroups);
  const slots = R32.filter((match) => match.awaySlot[0] === "T")
    .map((match) => ({
      n: match.n,
      options: match.awaySlot[1].split("").filter((group) => groupSet.has(group)),
    }))
    .sort((a, b) => a.options.length - b.options.length);

  const assignment: Record<number, string> = {};

  function backtrack(index: number, used: Set<string>): boolean {
    if (index === slots.length) return true;
    const slot = slots[index];
    for (const group of [...slot.options].sort()) {
      if (used.has(group)) continue;
      assignment[slot.n] = group;
      used.add(group);
      if (backtrack(index + 1, used)) return true;
      used.delete(group);
      delete assignment[slot.n];
    }
    return false;
  }

  if (!backtrack(0, new Set())) {
    const used = new Set<string>();
    for (const slot of slots) {
      const fallback = slot.options.find((group) => !used.has(group))
        ?? qualifiedGroups.find((group) => !used.has(group));
      if (!fallback) throw new Error(`No third-place assignment for match ${slot.n}`);
      assignment[slot.n] = fallback;
      used.add(fallback);
    }
  }

  return assignment;
}

export function buildR32(
  results: Record<string, Score>,
  matches: Match[],
  fairplay: Record<string, number> = {},
) {
  const { ranked, table } = computeStandings(results, matches, fairplay);
  const thirds = bestThirds(ranked, table, fairplay);
  const thirdByGroup = Object.fromEntries(thirds.map((team) => [TEAM_GROUP[team], team]));
  const thirdSlots = assignThirds(
    GROUP_CODES.filter((group) => thirdByGroup[group]).sort(),
  );

  function resolve(slot: Slot, matchNumber: number) {
    const [kind, value] = slot;
    if (kind === "W") return ranked[value][0];
    if (kind === "R") return ranked[value][1];
    const group = thirdSlots[matchNumber];
    const team = thirdByGroup[group];
    if (!team) throw new Error(`No qualified third for match ${matchNumber}`);
    return team;
  }

  const fixtures: ResolvedFixture[] = R32.map((match) => ({
    n: match.n,
    home: resolve(match.homeSlot, match.n),
    away: resolve(match.awaySlot, match.n),
    date: match.date,
    venue: match.venue,
    country: match.country,
  }));

  return { fixtures, ranked, table, thirds };
}
