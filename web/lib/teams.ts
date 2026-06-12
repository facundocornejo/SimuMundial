export const GROUPS = {
  A: ["Mexico", "South Africa", "South Korea", "Czech Republic"],
  B: ["Canada", "Switzerland", "Qatar", "Bosnia and Herzegovina"],
  C: ["Brazil", "Morocco", "Haiti", "Scotland"],
  D: ["United States", "Paraguay", "Australia", "Turkey"],
  E: ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
  F: ["Netherlands", "Japan", "Tunisia", "Sweden"],
  G: ["Belgium", "Egypt", "Iran", "New Zealand"],
  H: ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
  I: ["France", "Senegal", "Norway", "Iraq"],
  J: ["Argentina", "Algeria", "Austria", "Jordan"],
  K: ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
  L: ["England", "Croatia", "Ghana", "Panama"],
} as const;

export type GroupCode = keyof typeof GROUPS;
export type Team = (typeof GROUPS)[GroupCode][number];

export const GROUP_CODES = Object.keys(GROUPS) as GroupCode[];

export const TEAMS = GROUP_CODES.flatMap((group) => GROUPS[group]);

export const TEAM_GROUP = Object.fromEntries(
  GROUP_CODES.flatMap((group) => GROUPS[group].map((team) => [team, group])),
) as Record<string, GroupCode>;

export const ES: Record<string, string> = {
  Mexico: "México",
  "South Africa": "Sudáfrica",
  "South Korea": "Corea del Sur",
  "Czech Republic": "Chequia",
  Canada: "Canadá",
  Switzerland: "Suiza",
  Qatar: "Catar",
  "Bosnia and Herzegovina": "Bosnia y Herzegovina",
  Brazil: "Brasil",
  Morocco: "Marruecos",
  Haiti: "Haití",
  Scotland: "Escocia",
  "United States": "Estados Unidos",
  Paraguay: "Paraguay",
  Australia: "Australia",
  Turkey: "Turquía",
  Germany: "Alemania",
  Curaçao: "Curazao",
  "Ivory Coast": "Costa de Marfil",
  Ecuador: "Ecuador",
  Netherlands: "Países Bajos",
  Japan: "Japón",
  Tunisia: "Túnez",
  Sweden: "Suecia",
  Belgium: "Bélgica",
  Egypt: "Egipto",
  Iran: "Irán",
  "New Zealand": "Nueva Zelanda",
  Spain: "España",
  "Cape Verde": "Cabo Verde",
  "Saudi Arabia": "Arabia Saudita",
  Uruguay: "Uruguay",
  France: "Francia",
  Senegal: "Senegal",
  Norway: "Noruega",
  Iraq: "Irak",
  Argentina: "Argentina",
  Algeria: "Argelia",
  Austria: "Austria",
  Jordan: "Jordania",
  Portugal: "Portugal",
  Uzbekistan: "Uzbekistán",
  Colombia: "Colombia",
  "DR Congo": "RD Congo",
  England: "Inglaterra",
  Croatia: "Croacia",
  Ghana: "Ghana",
  Panama: "Panamá",
};
