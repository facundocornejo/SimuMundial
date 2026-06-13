# -*- coding: utf-8 -*-
"""Backtest rolling del modelo de grupos.

Mide log-loss 1X2 sobre partidos historicos antes de actualizar el Elo con el
resultado observado. El objetivo es comparar el modelo actual contra una
variante v2 sin tocar los picks congelados.

Salida: data/backtest_report.json
"""
import csv
import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from teams import canon

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "backtest_report.json"

START_ELO = 1500.0
HOME_ADV = 85.0
BASE_TOTAL = 2.55
MIN_LAMBDA = 0.18
MAX_G = 8
RHO_BASELINE = 1.10
RHO_DC = -0.10
BACKTEST_START = date(2022, 1, 1)
FORM_WINDOW_DAYS = 730
HALF_LIFE_DAYS = 548
SHRINKAGE_TARGET_MATCHES = 10
EPS = 1e-6


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def neutral_value(value):
    return (value or "").strip().upper() == "TRUE"


def k_factor(tournament):
    t = (tournament or "").lower()
    if "fifa world cup" in t and "qualification" not in t:
        return 60.0
    if "qualification" in t:
        return 40.0
    if any(x in t for x in (
        "euro", "copa américa", "copa america", "cup of nations",
        "asian cup", "gold cup", "concacaf championship",
        "confederations", "nations league", "oceania",
    )):
        return 50.0
    if "friendly" in t:
        return 20.0
    return 30.0


def margin_mult(goal_diff):
    gd = abs(goal_diff)
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return (11.0 + gd) / 8.0


def elo_we(diff):
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


def apply_match(elo, home, away, home_score, away_score, tournament, neutral):
    eh = elo[home]
    ea = elo[away]
    diff = eh - ea + (0.0 if neutral else HOME_ADV)
    expected_home = elo_we(diff)
    if home_score > away_score:
        result = 1.0
    elif home_score == away_score:
        result = 0.5
    else:
        result = 0.0
    delta = k_factor(tournament) * margin_mult(home_score - away_score) * (result - expected_home)
    elo[home] = eh + delta
    elo[away] = ea - delta


def poisson_pmf(lmb, goals):
    return math.exp(-lmb) * lmb ** goals / math.factorial(goals)


def dixon_coles_tau(home_goals, away_goals, lambda_home, lambda_away, rho):
    if home_goals == 0 and away_goals == 0:
        return 1.0 - lambda_home * lambda_away * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + lambda_home * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + lambda_away * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def build_matrix(lambda_home, lambda_away, mode):
    home = [poisson_pmf(lambda_home, i) for i in range(MAX_G + 1)]
    away = [poisson_pmf(lambda_away, j) for j in range(MAX_G + 1)]
    matrix = []
    for i in range(MAX_G + 1):
        row = []
        for j in range(MAX_G + 1):
            value = home[i] * away[j]
            if mode == "baseline" and i == j:
                value *= RHO_BASELINE
            elif mode == "v2":
                value *= max(0.05, dixon_coles_tau(i, j, lambda_home, lambda_away, RHO_DC))
            row.append(value)
        matrix.append(row)
    total = sum(sum(row) for row in matrix)
    return [[value / total for value in row] for row in matrix]


def matrix_probs(matrix):
    p1 = sum(matrix[i][j] for i in range(len(matrix)) for j in range(len(matrix)) if i > j)
    px = sum(matrix[i][i] for i in range(len(matrix)))
    p2 = 1.0 - p1 - px
    return p1, px, p2


def recent_records(records, as_of):
    cutoff = as_of - timedelta(days=FORM_WINDOW_DAYS)
    return [record for record in records if cutoff <= record["date"] < as_of]


def simple_average(records, key):
    if not records:
        return 0.0
    return sum(record[key] for record in records) / len(records)


def weighted_average(records, as_of, key):
    if not records:
        return 0.0, 0
    weighted_sum = 0.0
    total_weight = 0.0
    for record in records:
        days = max(0, (as_of - record["date"]).days)
        weight = 0.5 ** (days / HALF_LIFE_DAYS)
        weighted_sum += record[key] * weight
        total_weight += weight
    return (weighted_sum / total_weight if total_weight else 0.0), len(records)


def shrink(value, n, target):
    if n >= SHRINKAGE_TARGET_MATCHES:
        return value
    missing = SHRINKAGE_TARGET_MATCHES - n
    return (n * value + missing * target) / SHRINKAGE_TARGET_MATCHES


def profile(team, elo, recent, as_of, mode, global_gf, global_gc):
    rows = recent_records(recent[team], as_of)
    if mode == "baseline":
        avg_gf = simple_average(rows, "gf")
        avg_gc = simple_average(rows, "gc")
    else:
        avg_gf, n = weighted_average(rows, as_of, "gf")
        avg_gc, _ = weighted_average(rows, as_of, "gc")
        avg_gf = shrink(avg_gf, n, global_gf)
        avg_gc = shrink(avg_gc, n, global_gc)
    return {"elo": elo[team], "avg_gf_2y": avg_gf, "avg_gc_2y": avg_gc}


def lambdas(home_profile, away_profile, neutral):
    diff = home_profile["elo"] - away_profile["elo"] + (0.0 if neutral else HOME_ADV)
    we = elo_we(diff)
    attack = (
        home_profile["avg_gf_2y"] + away_profile["avg_gc_2y"]
        + away_profile["avg_gf_2y"] + home_profile["avg_gc_2y"]
    ) / 2.0
    total = max(1.8, min(3.6, 0.5 * BASE_TOTAL + 0.5 * attack))
    return max(MIN_LAMBDA, total * we), max(MIN_LAMBDA, total * (1.0 - we))


def log_loss(probs, home_score, away_score):
    if home_score > away_score:
        p = probs[0]
    elif home_score == away_score:
        p = probs[1]
    else:
        p = probs[2]
    return -math.log(max(EPS, min(1.0 - EPS, p)))


def read_history():
    rows = []
    with open(DATA / "history.csv", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            d = parse_date(row.get("date") or "")
            if not d:
                continue
            try:
                home_score = int(row["home_score"])
                away_score = int(row["away_score"])
            except (TypeError, ValueError):
                continue
            rows.append({
                "date": d,
                "home": canon(row["home_team"]),
                "away": canon(row["away_team"]),
                "home_score": home_score,
                "away_score": away_score,
                "tournament": row.get("tournament") or "",
                "neutral": neutral_value(row.get("neutral")),
            })
    rows.sort(key=lambda item: item["date"])
    return rows


def evaluate():
    elo = defaultdict(lambda: START_ELO)
    recent = defaultdict(list)
    totals = {
        "baseline": {"log_loss": 0.0, "n": 0},
        "v2_candidate": {"log_loss": 0.0, "n": 0},
    }
    global_goals = {"gf": 0.0, "gc": 0.0, "n": 0}

    for row in read_history():
        home = row["home"]
        away = row["away"]
        if row["date"] >= BACKTEST_START:
            if global_goals["n"]:
                global_gf = global_goals["gf"] / global_goals["n"]
                global_gc = global_goals["gc"] / global_goals["n"]
            else:
                global_gf = BASE_TOTAL / 2.0
                global_gc = BASE_TOTAL / 2.0
            for key, mode in (("baseline", "baseline"), ("v2_candidate", "v2")):
                home_profile = profile(home, elo, recent, row["date"], mode, global_gf, global_gc)
                away_profile = profile(away, elo, recent, row["date"], mode, global_gf, global_gc)
                lambda_home, lambda_away = lambdas(home_profile, away_profile, row["neutral"])
                probs = matrix_probs(build_matrix(lambda_home, lambda_away, mode))
                totals[key]["log_loss"] += log_loss(probs, row["home_score"], row["away_score"])
                totals[key]["n"] += 1

        apply_match(
            elo,
            home,
            away,
            row["home_score"],
            row["away_score"],
            row["tournament"],
            row["neutral"],
        )
        recent[home].append({"date": row["date"], "gf": row["home_score"], "gc": row["away_score"]})
        recent[away].append({"date": row["date"], "gf": row["away_score"], "gc": row["home_score"]})
        global_goals["gf"] += row["home_score"] + row["away_score"]
        global_goals["gc"] += row["away_score"] + row["home_score"]
        global_goals["n"] += 2

    report = {}
    for key, values in totals.items():
        n = values["n"]
        report[key] = {
            "matches": n,
            "log_loss": round(values["log_loss"] / n, 6) if n else None,
        }
    baseline = report["baseline"]["log_loss"]
    candidate = report["v2_candidate"]["log_loss"]
    report["decision"] = {
        "adopt_v2": candidate is not None and baseline is not None and candidate < baseline,
        "delta_log_loss": round(candidate - baseline, 6) if candidate is not None and baseline is not None else None,
        "note": "Menor log-loss es mejor. Odds y Elo externo no se evaluan historicamente por falta de serie historica.",
    }
    return {
        "updated": datetime.now().isoformat(timespec="seconds"),
        "backtest_start": BACKTEST_START.isoformat(),
        "constants": {
            "home_adv": HOME_ADV,
            "base_total": BASE_TOTAL,
            "rho_baseline": RHO_BASELINE,
            "rho_dc": RHO_DC,
            "half_life_days": HALF_LIFE_DAYS,
            "shrinkage_target_matches": SHRINKAGE_TARGET_MATCHES,
        },
        "results": report,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Ruta de salida alternativa")
    args = parser.parse_args(argv)
    out_path = Path(args.output) if args.output else OUT

    if not (DATA / "history.csv").exists():
        print("Falta data/history.csv: corre fetch_history.py primero")
        return 1
    result = evaluate()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    baseline = result["results"]["baseline"]["log_loss"]
    candidate = result["results"]["v2_candidate"]["log_loss"]
    decision = result["results"]["decision"]
    print(f"Backtest baseline log-loss: {baseline}")
    print(f"Backtest v2 candidate log-loss: {candidate} (delta {decision['delta_log_loss']})")
    print(f"Adoptar v2: {decision['adopt_v2']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
