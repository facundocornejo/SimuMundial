import type { Match } from "./types";

export function orderedMatchIds(matches: Pick<Match, "match_id">[]) {
  return matches.map((match) => match.match_id).sort();
}

export function groupMatches(matches: Match[]) {
  return matches.reduce<Record<string, Match[]>>((groups, match) => {
    groups[match.group] ??= [];
    groups[match.group].push(match);
    return groups;
  }, {});
}
