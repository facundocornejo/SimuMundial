import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { buildR32 } from "../lib/bracket";
import { rngFromProde, runKnockout } from "../lib/draw";
import { decodeProde, encodeProde } from "../lib/prode-codec";
import { isValidScore, normalizeImportedProde, validateProde } from "../lib/prode-validation";
import { scoreProde } from "../lib/scoring";
import type { FixtureData, Prode, ProfilesData } from "../lib/types";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");

function readJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(resolve(root, relativePath), "utf8")) as T;
}

const fixture = readJson<FixtureData>("data/fixture.json");
const facu = readJson<Prode>("prode/prode_facu.json");
const profiles = readJson<ProfilesData>("data/team_profiles.json");
const matchIds = fixture.matches.map((match) => match.match_id).sort();

const expectedRanked = {
  A: ["Mexico", "Czech Republic", "South Korea", "South Africa"],
  B: ["Switzerland", "Canada", "Bosnia and Herzegovina", "Qatar"],
  C: ["Brazil", "Morocco", "Scotland", "Haiti"],
  D: ["Turkey", "United States", "Paraguay", "Australia"],
  E: ["Ecuador", "Germany", "Ivory Coast", "Curaçao"],
  F: ["Netherlands", "Japan", "Sweden", "Tunisia"],
  G: ["Belgium", "Iran", "Egypt", "New Zealand"],
  H: ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde"],
  I: ["France", "Norway", "Senegal", "Iraq"],
  J: ["Argentina", "Austria", "Algeria", "Jordan"],
  K: ["Colombia", "Portugal", "Uzbekistan", "DR Congo"],
  L: ["England", "Croatia", "Panama", "Ghana"],
};

const expectedR32 = [
  { n: 73, home: "Czech Republic", away: "Canada" },
  { n: 74, home: "Ecuador", away: "Scotland" },
  { n: 75, home: "Netherlands", away: "Morocco" },
  { n: 76, home: "Brazil", away: "Japan" },
  { n: 77, home: "France", away: "Paraguay" },
  { n: 78, home: "Germany", away: "Norway" },
  { n: 79, home: "Mexico", away: "Saudi Arabia" },
  { n: 80, home: "England", away: "Senegal" },
  { n: 81, home: "Turkey", away: "Ivory Coast" },
  { n: 82, home: "Belgium", away: "Algeria" },
  { n: 83, home: "Portugal", away: "Croatia" },
  { n: 84, home: "Spain", away: "Austria" },
  { n: 85, home: "Switzerland", away: "Egypt" },
  { n: 86, home: "Argentina", away: "Uruguay" },
  { n: 87, home: "Colombia", away: "Panama" },
  { n: 88, home: "United States", away: "Iran" },
];

describe("Sprint 1 parity", () => {
  it("matches Python group standings and R32 fixtures", () => {
    const result = buildR32(facu.results, fixture.matches, fixture.fairplay);

    expect(result.ranked).toEqual(expectedRanked);
    expect(result.fixtures.map(({ n, home, away }) => ({ n, home, away }))).toEqual(expectedR32);
  });

  it("scores facu like the current juego.html snapshot", () => {
    expect(scoreProde(facu, fixture.matches)).toEqual({
      exact: 1,
      outcome: 0,
      points: 3,
    });
  });

  it("round-trips the compact prode code", () => {
    expect(decodeProde(encodeProde(facu, matchIds), matchIds)).toEqual({
      player: facu.player,
      results: facu.results,
    });
  });

  it("draws the same knockout for the same prode seed", () => {
    const r32 = buildR32(facu.results, fixture.matches, fixture.fairplay).fixtures;
    const first = runKnockout(r32, profiles.profiles, rngFromProde(facu));
    const second = runKnockout(r32, profiles.profiles, rngFromProde(facu));

    expect(second).toEqual(first);
  });
});

describe("Prode validation", () => {
  it("accepts a complete prode with 72 valid scores", () => {
    const report = validateProde(facu, matchIds);

    expect(report.valid).toBe(true);
    expect(report.imported).toBe(72);
    expect(report.missing).toEqual([]);
    expect(report.unknown).toEqual([]);
    expect(report.invalid).toEqual([]);
  });

  it("rejects an incomplete prode", () => {
    const [, ...rest] = Object.entries(facu.results);
    const incomplete: Prode = {
      player: facu.player,
      results: Object.fromEntries(rest),
    };
    const report = validateProde(incomplete, matchIds);

    expect(report.valid).toBe(false);
    expect(report.imported).toBe(71);
    expect(report.missing).toHaveLength(1);
  });

  it("rejects scores outside the 0-9 integer range", () => {
    expect(isValidScore([9, 0])).toBe(true);
    expect(isValidScore([10, 0])).toBe(false);
    expect(isValidScore([1.5, 0])).toBe(false);
  });

  it("reports unknown ids and invalid scores during import", () => {
    const [firstMatchId] = matchIds;
    const imported = normalizeImportedProde({
      player: " Facu  ",
      ignored: true,
      results: {
        [firstMatchId]: [2, 1],
        "match-that-does-not-exist": [1, 0],
        [matchIds[1]]: [11, 0],
      },
    }, matchIds);

    expect(imported.prode.player).toBe("Facu");
    expect(imported.report.imported).toBe(1);
    expect(imported.report.unknown).toEqual(["match-that-does-not-exist"]);
    expect(imported.report.invalid).toEqual([matchIds[1]]);
  });

  it("throws on invalid compact codes", () => {
    expect(() => decodeProde("codigo-no-valido!", matchIds)).toThrow();
    expect(() => decodeProde("abc", matchIds)).toThrow();
  });
});
