# -*- coding: utf-8 -*-
"""Calcula Elo propio + forma reciente + H2H desde data/history.csv.

- Elo: K segun importancia del torneo, multiplicador por margen de gol,
  +85 de localia cuando no es cancha neutral. Arranque 1500.
- Los partidos ya jugados del Mundial 2026 (fixture.json) se aplican al final
  (el CSV historico suele actualizarse con demora).

Salida: data/team_profiles.json
"""
import csv
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from teams import TEAMS, TEAM_GROUP, GROUPS, canon

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

HOME_ADV = 75.0  # calibrado por backtest (sweep validado) 2026-06-13; SYNC: predict.py / model.ts
START_ELO = 1500.0


def k_factor(tournament: str) -> float:
    t = (tournament or "").lower()
    if "fifa world cup" in t and "qualification" not in t:
        return 60.0
    if "qualification" in t:
        return 40.0
    if any(x in t for x in ("euro", "copa américa", "copa america", "cup of nations",
                            "asian cup", "gold cup", "concacaf championship",
                            "confederations", "nations league", "oceania")):
        return 50.0
    if "friendly" in t:
        return 20.0
    return 30.0


def margin_mult(gd: int) -> float:
    gd = abs(gd)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11.0 + gd) / 8.0


def expected(diff: float) -> float:
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


def apply_match(elo, home, away, hs, as_, tournament, neutral):
    eh = elo[home]
    ea = elo[away]
    diff = eh - ea + (0.0 if neutral else HOME_ADV)
    we = expected(diff)
    if hs > as_:
        res = 1.0
    elif hs == as_:
        res = 0.5
    else:
        res = 0.0
    delta = k_factor(tournament) * margin_mult(hs - as_) * (res - we)
    elo[home] = eh + delta
    elo[away] = ea - delta


def main():
    hist_path = DATA / "history.csv"
    if not hist_path.exists():
        print("Falta data/history.csv: corre fetch_history.py primero")
        return 1

    elo = defaultdict(lambda: START_ELO)
    recent = defaultdict(list)      # ultimos partidos de cada clasificado
    h2h = defaultdict(lambda: [0, 0, 0])  # (team, rival) -> [W, D, L] desde team
    today = date.today()
    two_years_ago = (today - timedelta(days=730)).isoformat()

    rivals = {t: set(GROUPS[TEAM_GROUP[t]]) - {t} for t in TEAMS}

    n = 0
    with open(hist_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                hs, as_ = int(row["home_score"]), int(row["away_score"])
            except (ValueError, TypeError):
                continue
            home, away = canon(row["home_team"]), canon(row["away_team"])
            d = row.get("date") or ""
            if not d:
                continue
            # evitar doble conteo con fixture.json
            if d >= "2026-06-11" and "fifa world cup" in (row["tournament"] or "").lower():
                continue
            neutral = (row.get("neutral", "").strip().upper() == "TRUE")
            apply_match(elo, home, away, hs, as_, row["tournament"], neutral)
            n += 1

            for team, gf, gc, opp in ((home, hs, as_, away), (away, as_, hs, home)):
                if team not in TEAMS:
                    continue
                recent[team].append({"date": d, "opp": opp, "gf": gf, "gc": gc,
                                     "tournament": row["tournament"]})
                if opp in rivals[team]:
                    i = 0 if gf > gc else (1 if gf == gc else 2)
                    h2h[(team, opp)][i] += 1

    # aplicar partidos ya jugados del Mundial 2026
    fixture_path = DATA / "fixture.json"
    wc_applied = 0
    if fixture_path.exists():
        fx = json.loads(fixture_path.read_text(encoding="utf-8"))
        for m in sorted(fx["matches"], key=lambda x: x["date"] or ""):
            if m["status"] != "played" or not m["score"]:
                continue
            hs, as_ = m["score"]
            neutral = m["home"] != m["venue_country"]
            apply_match(elo, m["home"], m["away"], hs, as_, "FIFA World Cup", neutral)
            wc_applied += 1
            for team, gf, gc, opp in ((m["home"], hs, as_, m["away"]),
                                      (m["away"], as_, hs, m["home"])):
                recent[team].append({"date": m["date"], "opp": opp, "gf": gf,
                                     "gc": gc, "tournament": "FIFA World Cup"})
                if opp in rivals[team]:
                    i = 0 if gf > gc else (1 if gf == gc else 2)
                    h2h[(team, opp)][i] += 1

    profiles = {}
    for t in sorted(TEAMS):
        matches = sorted(recent[t], key=lambda m: m["date"] or "")
        last10 = matches[-10:]
        last2y = [m for m in matches if m["date"] >= two_years_ago]
        gp = max(len(last2y), 1)
        wdl = [sum(1 for m in last10 if m["gf"] > m["gc"]),
               sum(1 for m in last10 if m["gf"] == m["gc"]),
               sum(1 for m in last10 if m["gf"] < m["gc"])]
        profiles[t] = {
            "elo": round(elo[t], 1),
            "group": TEAM_GROUP[t],
            "form_last10": wdl,                       # [W, D, L]
            "avg_gf_2y": round(sum(m["gf"] for m in last2y) / gp, 3),
            "avg_gc_2y": round(sum(m["gc"] for m in last2y) / gp, 3),
            "matches_2y": len(last2y),
            "last10": [{"date": m["date"], "opp": m["opp"],
                        "score": f"{m['gf']}-{m['gc']}"} for m in last10],
            "h2h_group": {opp: h2h[(t, opp)] for opp in sorted(rivals[t])},
        }

    # ranking FIFA informativo si existe
    rk_path = DATA / "rankings.json"
    if rk_path.exists():
        fifa = json.loads(rk_path.read_text(encoding="utf-8")).get("fifa_ranking", {})
        for t, p in profiles.items():
            p["fifa_rank"] = fifa.get(t)

    with open(DATA / "team_profiles.json", "w", encoding="utf-8") as f:
        json.dump({"history_matches_used": n, "wc2026_applied": wc_applied,
                   "profiles": profiles}, f, ensure_ascii=False, indent=1)

    top = sorted(profiles.items(), key=lambda kv: -kv[1]["elo"])[:5]
    print(f"OK team_profiles.json ({n} partidos historicos + {wc_applied} del Mundial)")
    print("  Top-5 Elo:", ", ".join(f"{t} {p['elo']:.0f}" for t, p in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
