# -*- coding: utf-8 -*-
"""Fetch externo de Elo mundial desde eloratings.net.

Salida: data/elo_world.json

El script es best-effort: si no hay red, si cambia el formato o si se corre
con --offline sin fixture, deja el pipeline vivo. Para tests locales/CI acepta
--fixture con un TSV chico.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from teams import TEAMS, canon

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "elo_world.json"
URL = "https://www.eloratings.net/World.tsv"
HEADERS = {"User-Agent": "Mozilla/5.0 (SimuMundial pipeline; uso personal de analisis)"}
CACHE_TTL = timedelta(hours=12)

EXTRA_ALIASES = {
    "USA": "United States",
    "U.S.A.": "United States",
    "Korea Republic": "South Korea",
    "South Korea": "South Korea",
    "Czechia": "Czech Republic",
    "Congo DR": "DR Congo",
    "Cape Verde Islands": "Cape Verde",
    "Curacao": "Curaçao",
}

CODE_TO_TEAM = {
    "AL": "Albania",
    "AR": "Argentina",
    "AT": "Austria",
    "AU": "Australia",
    "BA": "Bosnia and Herzegovina",
    "BE": "Belgium",
    "BR": "Brazil",
    "CA": "Canada",
    "CD": "DR Congo",
    "CH": "Switzerland",
    "CI": "Ivory Coast",
    "CO": "Colombia",
    "CV": "Cape Verde",
    "CW": "Curaçao",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DZ": "Algeria",
    "EC": "Ecuador",
    "EG": "Egypt",
    "EN": "England",
    "ES": "Spain",
    "FR": "France",
    "GH": "Ghana",
    "HR": "Croatia",
    "HT": "Haiti",
    "IQ": "Iraq",
    "IR": "Iran",
    "JO": "Jordan",
    "JP": "Japan",
    "KR": "South Korea",
    "MA": "Morocco",
    "MX": "Mexico",
    "NL": "Netherlands",
    "NO": "Norway",
    "NZ": "New Zealand",
    "PA": "Panama",
    "PT": "Portugal",
    "PY": "Paraguay",
    "QA": "Qatar",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "SN": "Senegal",
    "SQ": "Scotland",
    "TN": "Tunisia",
    "TR": "Turkey",
    "US": "United States",
    "UY": "Uruguay",
    "UZ": "Uzbekistan",
    "ZA": "South Africa",
}


def canonical(name):
    return EXTRA_ALIASES.get((name or "").strip(), canon(name))


def load_env_file(path=ROOT / ".env"):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def cache_fresh(path=OUT):
    if not path.exists():
        return False
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if len(cached.get("elo", {})) < len(TEAMS):
            return False
    except Exception:
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < CACHE_TTL


def numeric(value):
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def parse_tsv(text):
    """Parsea TSV de eloratings con heuristica defensiva de columnas.

    En World.tsv suelen venir columnas posicionales; para no depender de un
    indice fragil buscamos un nombre canonico y el primer numero plausible de
    rating (>1000) despues de la columna del equipo.
    """
    ratings = {}
    unmatched = set(TEAMS)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        cols = [c.strip() for c in line.split("\t")]

        if len(cols) >= 4 and cols[2] in CODE_TO_TEAM:
            team = CODE_TO_TEAM[cols[2]]
            rating = numeric(cols[3])
            if team in TEAMS and rating is not None:
                ratings[team] = int(round(rating))
                unmatched.discard(team)
                continue

        team = None
        team_index = -1
        for index, col in enumerate(cols):
            candidate = canonical(col)
            if candidate in TEAMS:
                team = candidate
                team_index = index
                break
        if not team:
            continue

        numbers = []
        for col in cols[team_index + 1:] + cols[:team_index]:
            value = numeric(col)
            if value is not None and 1000 <= value <= 2600:
                numbers.append(value)
        if not numbers:
            continue
        ratings[team] = int(round(numbers[0]))
        unmatched.discard(team)

    return ratings, sorted(unmatched)


def read_source(args):
    if args.fixture:
        return Path(args.fixture).read_text(encoding="utf-8"), "fixture"
    if args.offline:
        print("[aviso] fetch_elo en modo offline sin fixture; sigo sin Elo externo")
        return "", "offline"

    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.text, URL


def write_output(path, ratings, source, unmatched):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "elo": ratings,
        "unmatched": unmatched,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv=None):
    load_env_file()
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="TSV local para tests offline")
    parser.add_argument("--offline", action="store_true", help="No intenta red")
    parser.add_argument("--force", action="store_true", help="Ignora cache")
    parser.add_argument("--output", help="Ruta de salida alternativa para tests")
    args = parser.parse_args(argv)
    out_path = Path(args.output) if args.output else OUT

    if not args.force and not args.fixture and not args.offline and cache_fresh(out_path):
        cached = json.loads(out_path.read_text(encoding="utf-8"))
        print(f"OK elo_world.json cache: {len(cached.get('elo', {}))}/{len(TEAMS)} equipos")
        return 0

    try:
        text, source = read_source(args)
        ratings, unmatched = parse_tsv(text)
    except Exception as exc:
        print(f"[aviso] No pude bajar Elo externo ({exc}); sigo solo con Elo propio")
        ratings, unmatched, source = {}, sorted(TEAMS), "error"

    if unmatched:
        print(f"  [aviso] Elo externo sin match para {len(unmatched)} equipos: {', '.join(unmatched[:10])}")
    write_output(out_path, ratings, source, unmatched)
    print(f"OK elo_world.json: {len(ratings)}/{len(TEAMS)} equipos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
