import type { Prode, Score } from "./types";

export type ProdeValidation = {
  valid: boolean;
  player: string;
  imported: number;
  missing: string[];
  unknown: string[];
  invalid: string[];
  errors: string[];
};

export type NormalizedProde = {
  prode: Prode;
  report: ProdeValidation;
};

export function sanitizePlayerName(value: unknown) {
  const name = String(value ?? "").replace(/\s+/g, " ").trim();
  return name.slice(0, 36);
}

export function isValidScore(value: unknown): value is Score {
  return Array.isArray(value)
    && value.length === 2
    && Number.isInteger(value[0])
    && Number.isInteger(value[1])
    && value[0] >= 0
    && value[0] <= 9
    && value[1] >= 0
    && value[1] <= 9;
}

export function clampGoal(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return 0;
  return Math.max(0, Math.min(9, Math.trunc(numeric)));
}

export function normalizeScore(value: unknown): Score | null {
  return isValidScore(value) ? value : null;
}

export function normalizeImportedProde(value: unknown, matchIds: string[]): NormalizedProde {
  const source = value && typeof value === "object" ? value as Partial<Prode> : {};
  const known = new Set(matchIds);
  const results: Record<string, Score> = {};
  const unknown: string[] = [];
  const invalid: string[] = [];

  for (const [matchId, rawScore] of Object.entries(source.results ?? {})) {
    if (!known.has(matchId)) {
      unknown.push(matchId);
      continue;
    }
    const score = normalizeScore(rawScore);
    if (!score) {
      invalid.push(matchId);
      continue;
    }
    results[matchId] = score;
  }

  const player = sanitizePlayerName(source.player);
  const prode: Prode = {
    player,
    results,
  };

  return {
    prode,
    report: validateProde(prode, matchIds, { unknown, invalid }),
  };
}

export function validateProde(
  prode: Prode,
  matchIds: string[],
  found: { unknown?: string[]; invalid?: string[] } = {},
): ProdeValidation {
  const known = new Set(matchIds);
  const unknown = [...(found.unknown ?? [])];
  const invalid = [...(found.invalid ?? [])];
  const errors: string[] = [];
  const player = sanitizePlayerName(prode.player);

  if (!player) errors.push("Falta el nombre.");

  for (const [matchId, score] of Object.entries(prode.results ?? {})) {
    if (!known.has(matchId) && !unknown.includes(matchId)) unknown.push(matchId);
    if (known.has(matchId) && !isValidScore(score) && !invalid.includes(matchId)) invalid.push(matchId);
  }

  const missing = matchIds.filter((matchId) => !isValidScore(prode.results?.[matchId]));
  if (missing.length > 0) errors.push(`Faltan ${missing.length} partidos.`);
  if (unknown.length > 0) errors.push(`${unknown.length} partidos no existen en el fixture.`);
  if (invalid.length > 0) errors.push(`${invalid.length} resultados tienen formato invalido.`);

  return {
    valid: errors.length === 0,
    player,
    imported: matchIds.length - missing.length,
    missing,
    unknown,
    invalid,
    errors,
  };
}
