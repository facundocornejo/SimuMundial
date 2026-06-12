export type Score = [number, number];

export type Match = {
  match_id: string;
  group: string;
  home: string;
  away: string;
  home_es?: string;
  away_es?: string;
  date?: string;
  time?: string;
  venue?: string;
  venue_country?: string;
  status?: "played" | "pending";
  score?: Score | null;
};

export type FixtureData = {
  updated?: string;
  source?: string;
  fairplay?: Record<string, number>;
  matches: Match[];
};

export type TeamProfile = {
  elo: number;
  group?: string;
  avg_gf_2y: number;
  avg_gc_2y: number;
  fifa_rank?: number | null;
  [key: string]: unknown;
};

export type ProfilesData = {
  profiles: Record<string, TeamProfile>;
};

export type Prode = {
  player: string;
  created?: string;
  results: Record<string, Score>;
};
