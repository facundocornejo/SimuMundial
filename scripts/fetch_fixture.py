# -*- coding: utf-8 -*-
"""Baja el fixture + resultados de la fase de grupos del Mundial 2026.

Fuente primaria: paginas de Wikipedia por grupo (2026_FIFA_World_Cup_Group_A..L)
Fuente opcional: football-data.org si existe la variable FOOTBALL_DATA_KEY.

Salida: data/fixture.json
"""
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from teams import GROUPS, TEAMS, canon, venue_country, ES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WIKI = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_Group_{g}"
HEADERS = {"User-Agent": "Mozilla/5.0 (mundial2026-pipeline; uso personal de analisis)"}

SCORE_RE = re.compile(r"^(\d+)\s*[–\-—]\s*(\d+)")
ISO_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})")
DATE_RE2 = re.compile(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)?", re.I)
MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}


def parse_footballbox(box, group):
    text = box.get_text(" ", strip=True)

    home_el = box.select_one(".fhome")
    away_el = box.select_one(".faway")
    score_el = box.select_one(".fscore")
    if not (home_el and away_el):
        return None
    home = canon(home_el.get_text(" ", strip=True))
    away = canon(away_el.get_text(" ", strip=True))
    if home not in TEAMS or away not in TEAMS:
        return None

    # fecha: ISO oculto (span.bday) o formato US "June 11, 2026" o "11 June 2026"
    date = None
    m = ISO_RE.search(text)
    if m:
        date = m.group(1)
    else:
        m = DATE_RE.search(text)
        if m:
            date = f"{int(m.group(3)):04d}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"
        else:
            m = DATE_RE2.search(text)
            if m:
                date = f"{int(m.group(3)):04d}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"

    # hora local: "1:00 p.m." -> 13:00
    time = None
    time_el = box.select_one(".ftime") or box.select_one(".fdate")
    blob = time_el.get_text(" ", strip=True) if time_el else text
    m = TIME_RE.search(blob)
    if m:
        h, mn, ampm = int(m.group(1)), m.group(2), (m.group(3) or "").lower().replace(".", "")
        if ampm == "pm" and h != 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        time = f"{h:02d}:{mn}"

    # marcador
    score = None
    status = "pending"
    if score_el:
        m = SCORE_RE.match(score_el.get_text(" ", strip=True))
        if m:
            score = [int(m.group(1)), int(m.group(2))]
            status = "played"

    # sede
    venue = ""
    fright = box.select_one(".fright")
    if fright:
        venue = fright.get_text(" ", strip=True)
        venue = re.sub(r"Attendance.*$", "", venue, flags=re.I).strip()
        venue = re.sub(r"Referee.*$", "", venue, flags=re.I).strip()

    return {
        "group": group,
        "home": home, "away": away,
        "home_es": ES[home], "away_es": ES[away],
        "date": date, "time": time,
        "venue": venue,
        "venue_country": venue_country(venue),
        "status": status, "score": score,
    }


def parse_discipline(soup, group):
    """Puntos de fair play por equipo (deduccion FIFA: mas negativo = peor).
    Devuelve {equipo: puntos_negativos} o {} si no se puede parsear."""
    out = {}
    anchor = soup.find(id="Discipline")
    if not anchor:
        return out
    table = anchor.find_parent().find_next("table")
    if not table:
        return out
    for row in table.select("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        name = canon(cells[0].get_text(" ", strip=True))
        if name not in GROUPS[group]:
            continue
        nums = []
        for c in cells[1:]:
            t = c.get_text(" ", strip=True).replace("−", "-")
            if re.fullmatch(r"-?\d+", t):
                nums.append(int(t))
        if nums:
            out[name] = nums[-1]  # ultima columna = deduccion total
    return out


def fetch_from_wikipedia():
    matches, fairplay = [], {}
    for g in GROUPS:
        url = WIKI.format(g=g)
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        boxes = soup.select("div.footballbox")
        parsed = [m for m in (parse_footballbox(b, g) for b in boxes) if m]
        if len(parsed) != 6:
            print(f"  [aviso] Grupo {g}: se esperaban 6 partidos, se parsearon {len(parsed)}")
        matches.extend(parsed)
        fairplay.update(parse_discipline(soup, g))
        print(f"  Grupo {g}: {len(parsed)} partidos ({sum(1 for m in parsed if m['status']=='played')} jugados)")
    return matches, fairplay


def fetch_from_api(key):
    """football-data.org v4. Devuelve lista de partidos o None si falla."""
    try:
        r = requests.get(
            "https://api.football-data.org/v4/competitions/WC/matches",
            headers={"X-Auth-Token": key}, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [aviso] API football-data fallo ({e}); uso Wikipedia")
        return None
    out = []
    for m in data.get("matches", []):
        if m.get("stage") != "GROUP_STAGE":
            continue
        home = canon(m["homeTeam"]["name"]); away = canon(m["awayTeam"]["name"])
        if home not in TEAMS or away not in TEAMS:
            continue
        ft = m.get("score", {}).get("fullTime", {})
        played = m.get("status") in ("FINISHED", "AWARDED")
        group = (m.get("group") or "").replace("GROUP_", "")
        out.append({
            "group": group, "home": home, "away": away,
            "home_es": ES[home], "away_es": ES[away],
            "date": m["utcDate"][:10], "time": m["utcDate"][11:16] + " UTC",
            "venue": m.get("venue") or "", "venue_country": venue_country(m.get("venue") or ""),
            "status": "played" if played else "pending",
            "score": [ft.get("home"), ft.get("away")] if played else None,
        })
    return out or None


def main():
    DATA.mkdir(exist_ok=True)
    matches = None
    key = os.environ.get("FOOTBALL_DATA_KEY")
    if key:
        print("Fixture: intento via football-data.org...")
        matches = fetch_from_api(key)
    fairplay = {}
    if matches is None:
        print("Fixture: scraping Wikipedia (grupos A-L)...")
        matches, fairplay = fetch_from_wikipedia()

    # IDs estables: orden cronologico dentro de cada grupo
    for g in GROUPS:
        gms = sorted([m for m in matches if m["group"] == g],
                     key=lambda m: (m["date"] or "9999", m["time"] or "99:99"))
        for i, m in enumerate(gms, 1):
            m["match_id"] = f"2026-{g}-{i:02d}"
    matches.sort(key=lambda m: (m["date"] or "9999", m["time"] or "99:99", m["group"]))

    out = {
        "updated": datetime.now().isoformat(timespec="seconds"),
        "source": "football-data.org" if key and matches else "wikipedia",
        "fairplay": fairplay,
        "matches": matches,
    }
    with open(DATA / "fixture.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    played = sum(1 for m in matches if m["status"] == "played")
    print(f"OK fixture.json: {len(matches)} partidos, {played} jugados, fairplay de {len(fairplay)} equipos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
