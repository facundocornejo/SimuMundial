import type { Prode, Score } from "./types";
import { isValidScore, sanitizePlayerName } from "./prode-validation";

const SEP = "|";
const CODE_RE = /^[A-Za-z0-9_-]+$/;

function toBase64Url(value: string) {
  if (typeof btoa === "function") {
    return btoa(unescape(encodeURIComponent(value)))
      .replaceAll("+", "-")
      .replaceAll("/", "_")
      .replaceAll("=", "");
  }
  return Buffer.from(value, "utf8").toString("base64url");
}

function fromBase64Url(value: string) {
  if (!CODE_RE.test(value)) throw new Error("Codigo de prode invalido");
  const normalized = value.replaceAll("-", "+").replaceAll("_", "/");
  if (typeof atob === "function") {
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    return decodeURIComponent(escape(atob(padded)));
  }
  return Buffer.from(value, "base64url").toString("utf8");
}

export function compactProde(prode: Prode, matchIds: string[]) {
  const payload = matchIds
    .map((matchId) => {
      const score = prode.results[matchId];
      if (!isValidScore(score)) return "__";
      return `${score[0]}${score[1]}`;
    })
    .join("");
  return `${encodeURIComponent(sanitizePlayerName(prode.player))}${SEP}${payload}`;
}

export function expandCompactProde(raw: string, matchIds: string[]): Prode {
  if (!raw.includes(SEP)) throw new Error("Codigo de prode incompleto");
  const [encodedName, payload = ""] = raw.split(SEP);
  const results: Record<string, Score> = {};

  matchIds.forEach((matchId, index) => {
    const pair = payload.slice(index * 2, index * 2 + 2);
    if (!pair || pair === "__") return;
    const home = Number(pair[0]);
    const away = Number(pair[1]);
    const score: Score = [home, away];
    if (isValidScore(score)) {
      results[matchId] = score;
    }
  });

  return {
    player: sanitizePlayerName(decodeURIComponent(encodedName || "sin-nombre")),
    results,
  };
}

export function encodeProde(prode: Prode, matchIds: string[]) {
  return toBase64Url(compactProde(prode, matchIds));
}

export function decodeProde(code: string, matchIds: string[]) {
  return expandCompactProde(fromBase64Url(code), matchIds);
}
