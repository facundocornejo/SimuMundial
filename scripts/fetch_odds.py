# -*- coding: utf-8 -*-
"""Fetch de cuotas 1X2 desde The Odds API.

Salida: data/odds.json

El script es best-effort y soporta fixtures locales para poder testear sin red
ni token. Las probabilidades se guardan en escala 0..1.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from teams import canon

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "odds.json"
FIXTURE = DATA / "fixture.json"
SPORT_KEY = "soccer_fifa_world_cup"
URL = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds/"
CACHE_TTL = timedelta(hours=12)
HEADERS = {"User-Agent": "Mozilla/5.0 (SimuMundial pipeline; uso personal de analisis)"}

EXTRA_ALIASES = {
    "Draw": "Draw",
    "Tie": "Draw",
    "USA": "United States",
    "U.S.A.": "United States",
    "Korea Republic": "South Korea",
    "Czechia": "Czech Republic",
    "Congo DR": "DR Congo",
    "Cape Verde Islands": "Cape Verde",
    "Curacao": "Curaçao",
}


def canonical(name):
    raw = (name or "").strip()
    return EXTRA_ALIASES.get(raw, canon(raw))


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
        if not cached.get("odds"):
            return False
    except Exception:
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < CACHE_TTL


def load_fixture():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    by_ordered = {}
    by_pair = defaultdict(list)
    for match in data["matches"]:
        key = (match["home"], match["away"], match.get("date"))
        by_ordered[key] = match
        by_pair[frozenset((match["home"], match["away"]))].append(match)
    return by_ordered, by_pair


def match_event(event, by_ordered, by_pair):
    home = canonical(event.get("home_team"))
    away = canonical(event.get("away_team"))
    date = (event.get("commence_time") or "")[:10] or None

    direct = by_ordered.get((home, away, date))
    if direct:
        return direct, False

    reverse = by_ordered.get((away, home, date))
    if reverse:
        return reverse, True

    candidates = by_pair.get(frozenset((home, away)), [])
    if len(candidates) == 1:
        match = candidates[0]
        return match, match["home"] != home
    return None, False


def event_prices(event):
    home = canonical(event.get("home_team"))
    away = canonical(event.get("away_team"))
    rows = []

    for bookmaker in event.get("bookmakers", []):
        market = next((m for m in bookmaker.get("markets", []) if m.get("key") == "h2h"), None)
        if not market:
            continue
        prices = {}
        for outcome in market.get("outcomes", []):
            name = canonical(outcome.get("name"))
            price = outcome.get("price")
            if not isinstance(price, (int, float)) or price <= 1:
                continue
            if name == home:
                prices["home"] = float(price)
            elif name == away:
                prices["away"] = float(price)
            elif name == "Draw":
                prices["draw"] = float(price)
        if {"home", "draw", "away"} <= prices.keys():
            rows.append(prices)

    return rows


def normalize_probabilities(avg_home, avg_draw, avg_away):
    raw = [1.0 / avg_home, 1.0 / avg_draw, 1.0 / avg_away]
    total = sum(raw)
    return [value / total for value in raw]


def parse_events(events):
    by_ordered, by_pair = load_fixture()
    odds = {}
    unmatched = []

    for event in events:
        match, reversed_order = match_event(event, by_ordered, by_pair)
        if not match:
            unmatched.append({
                "home_team": event.get("home_team"),
                "away_team": event.get("away_team"),
                "commence_time": event.get("commence_time"),
            })
            continue

        rows = event_prices(event)
        if not rows:
            continue
        avg_home = sum(row["home"] for row in rows) / len(rows)
        avg_draw = sum(row["draw"] for row in rows) / len(rows)
        avg_away = sum(row["away"] for row in rows) / len(rows)
        p_home, p_draw, p_away = normalize_probabilities(avg_home, avg_draw, avg_away)

        if reversed_order:
            p1, p2 = p_away, p_home
        else:
            p1, p2 = p_home, p_away
        odds[match["match_id"]] = {
            "p1": round(p1, 4),
            "px": round(p_draw, 4),
            "p2": round(p2, 4),
            "bookmakers": len(rows),
        }

    return odds, unmatched


def fetch_events(args):
    if args.fixture:
        return json.loads(Path(args.fixture).read_text(encoding="utf-8")), "fixture", None
    if args.offline:
        print("[aviso] fetch_odds en modo offline sin fixture; sigo sin cuotas")
        return [], "offline", None

    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        print("[aviso] Falta ODDS_API_KEY; sigo sin cuotas")
        return [], "missing-key", None

    response = requests.get(
        URL,
        params={"apiKey": api_key, "regions": "eu", "markets": "h2h"},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json(), URL, response.headers.get("x-requests-remaining")


def write_output(path, odds, source, requests_remaining, unmatched):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now().isoformat(timespec="seconds"),
        "source": source,
        "requests_remaining": requests_remaining,
        "odds": odds,
        "unmatched": unmatched,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def main(argv=None):
    load_env_file()
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", help="JSON local con eventos de The Odds API")
    parser.add_argument("--offline", action="store_true", help="No intenta red")
    parser.add_argument("--force", action="store_true", help="Ignora cache")
    parser.add_argument("--output", help="Ruta de salida alternativa para tests")
    args = parser.parse_args(argv)
    out_path = Path(args.output) if args.output else OUT

    if not args.force and not args.fixture and not args.offline and cache_fresh(out_path):
        cached = json.loads(out_path.read_text(encoding="utf-8"))
        print(f"OK odds.json cache: {len(cached.get('odds', {}))} partidos")
        return 0

    try:
        events, source, requests_remaining = fetch_events(args)
        odds, unmatched = parse_events(events)
    except Exception as exc:
        print(f"[aviso] No pude bajar cuotas ({exc}); sigo sin mercado")
        odds, unmatched, source, requests_remaining = {}, [], "error", None

    if unmatched:
        print(f"  [aviso] Cuotas sin match para {len(unmatched)} eventos")
    write_output(out_path, odds, source, requests_remaining, unmatched)
    print(f"OK odds.json: {len(odds)} partidos con mercado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
