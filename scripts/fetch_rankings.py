# -*- coding: utf-8 -*-
"""Scrapea el ranking FIFA vigente desde Wikipedia (best-effort, informativo).

Salida: data/rankings.json  {"FIFA ranking": {team: rank}}
Si falla, el pipeline sigue: el modelo usa el Elo propio.
"""
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from teams import TEAMS, canon

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
URL = "https://en.wikipedia.org/wiki/FIFA_Men%27s_World_Ranking"
HEADERS = {"User-Agent": "Mozilla/5.0 (mundial2026-pipeline; uso personal de analisis)"}


def main():
    DATA.mkdir(exist_ok=True)
    ranks = {}
    try:
        r = requests.get(URL, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for table in soup.select("table.wikitable"):
            for row in table.select("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                team, rank = None, None
                for c in cells:
                    t = canon(c.get_text(" ", strip=True))
                    if t in TEAMS and team is None:
                        team = t
                    m = re.fullmatch(r"\d{1,3}", c.get_text(" ", strip=True))
                    if m and rank is None and 1 <= int(m.group()) <= 211:
                        rank = int(m.group())
                if team and rank and (team not in ranks or rank < ranks[team]):
                    ranks[team] = rank
    except Exception as e:
        print(f"[aviso] No pude scrapear el ranking FIFA ({e}); sigo solo con Elo")

    with open(DATA / "rankings.json", "w", encoding="utf-8") as f:
        json.dump({"fifa_ranking": ranks}, f, ensure_ascii=False, indent=1)
    print(f"OK rankings.json: ranking FIFA de {len(ranks)}/{len(TEAMS)} clasificados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
