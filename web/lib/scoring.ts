import type { Match, Prode, Score } from "./types";

export const PTS_EXACT = 3;
export const PTS_OUTCOME = 1;
export const PTS_QUALIFIED = 2;
export const PTS_CHAMPION = 10;

export type ScoreSummary = {
  exact: number;
  outcome: number;
  points: number;
};

function sign(value: number) {
  return value > 0 ? 1 : value < 0 ? -1 : 0;
}

export function sameScore(a: Score, b: Score) {
  return a[0] === b[0] && a[1] === b[1];
}

export function sameOutcome(a: Score, b: Score) {
  return sign(a[0] - a[1]) === sign(b[0] - b[1]);
}

export function scoreProde(prode: Prode, matches: Match[]): ScoreSummary {
  return matches.reduce<ScoreSummary>(
    (summary, match) => {
      if (match.status !== "played" || !match.score) return summary;
      const prediction = prode.results[match.match_id];
      if (!prediction) return summary;
      if (sameScore(prediction, match.score)) {
        summary.exact += 1;
        summary.points += PTS_EXACT;
      } else if (sameOutcome(prediction, match.score)) {
        summary.outcome += 1;
        summary.points += PTS_OUTCOME;
      }
      return summary;
    },
    { exact: 0, outcome: 0, points: 0 },
  );
}
