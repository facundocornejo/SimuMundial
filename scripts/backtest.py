# -*- coding: utf-8 -*-
"""Backtest rolling del modelo de grupos.

Mide log-loss 1X2 sobre partidos historicos antes de actualizar el Elo con el
resultado observado. El objetivo es comparar el modelo actual contra una
variante v2 sin tocar los picks congelados.

Tambien evalua si los datos externos (Elo de eloratings.net y cuotas de
mercado) pueden mejorar el baseline, con dos advertencias metodologicas duras:

  * data/elo_world.json es un SNAPSHOT actual, no una serie historica. Usar el
    rating de hoy para predecir un partido de 2023 mete look-ahead bias (el
    rating ya incorpora ese resultado). Por eso el blend de Elo externo se
    evalua solo sobre el subconjunto de partidos donde ambos equipos tienen
    rating externo, y SIEMPRE contra un baseline calculado sobre ESE mismo
    subconjunto (no contra el log-loss global). Como el leakage favorece al
    blend, solo un FRACASO en superar al baseline del subconjunto es
    concluyente; una mejora es no concluyente.
  * data/odds.json solo trae partidos futuros del Mundial 2026: cero
    solapamiento con el historial. El blend de mercado no es backtesteable.

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

ELO_BLEND_WEIGHTS = [0.1, 0.2, 0.3, 0.4, 0.5]
ODDS_BLEND_WEIGHTS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

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


def own_diff(home_profile, away_profile, neutral):
    return home_profile["elo"] - away_profile["elo"] + (0.0 if neutral else HOME_ADV)


def lambdas_from_diff(diff, home_profile, away_profile):
    """Reparte el total de goles esperado segun un diff de Elo dado.

    El total (cantidad de goles) depende solo del ataque/defensa reciente; el
    diff solo decide como se reparte entre local y visitante. Asi el blend de
    Elo externo afecta unicamente la probabilidad 1X2, no el over.
    """
    we = elo_we(diff)
    attack = (
        home_profile["avg_gf_2y"] + away_profile["avg_gc_2y"]
        + away_profile["avg_gf_2y"] + home_profile["avg_gc_2y"]
    ) / 2.0
    total = max(1.8, min(3.6, 0.5 * BASE_TOTAL + 0.5 * attack))
    return max(MIN_LAMBDA, total * we), max(MIN_LAMBDA, total * (1.0 - we))


def lambdas(home_profile, away_profile, neutral):
    return lambdas_from_diff(own_diff(home_profile, away_profile, neutral), home_profile, away_profile)


def load_external_elo():
    """Elo de eloratings.net mapeado a nombres canonicos. {} si no existe."""
    path = DATA / "elo_world.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8")).get("elo", {})
    return {canon(name): float(value) for name, value in raw.items()}


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

    external_elo = load_external_elo()
    # Subconjunto donde ambos equipos tienen Elo externo. Baseline propio del
    # subconjunto + un acumulador por peso de blend. Mismo modo "baseline".
    ext_blend = {
        "baseline_subset": {"log_loss": 0.0, "n": 0},
        "weights": {f"{w:.1f}": {"log_loss": 0.0, "n": 0} for w in ELO_BLEND_WEIGHTS},
    }

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
            profiles_cache = {}
            for key, mode in (("baseline", "baseline"), ("v2_candidate", "v2")):
                home_profile = profile(home, elo, recent, row["date"], mode, global_gf, global_gc)
                away_profile = profile(away, elo, recent, row["date"], mode, global_gf, global_gc)
                profiles_cache[mode] = (home_profile, away_profile)
                lambda_home, lambda_away = lambdas(home_profile, away_profile, row["neutral"])
                probs = matrix_probs(build_matrix(lambda_home, lambda_away, mode))
                totals[key]["log_loss"] += log_loss(probs, row["home_score"], row["away_score"])
                totals[key]["n"] += 1

            # Blend de Elo externo: solo si ambos equipos estan rateados.
            if home in external_elo and away in external_elo:
                hp, ap = profiles_cache["baseline"]
                d_own = own_diff(hp, ap, row["neutral"])
                d_ext = external_elo[home] - external_elo[away] + (0.0 if row["neutral"] else HOME_ADV)
                # baseline restringido al subconjunto (comparacion justa)
                lh, la = lambdas_from_diff(d_own, hp, ap)
                base_probs = matrix_probs(build_matrix(lh, la, "baseline"))
                ext_blend["baseline_subset"]["log_loss"] += log_loss(base_probs, row["home_score"], row["away_score"])
                ext_blend["baseline_subset"]["n"] += 1
                for w in ELO_BLEND_WEIGHTS:
                    d_blend = (1.0 - w) * d_own + w * d_ext
                    lh, la = lambdas_from_diff(d_blend, hp, ap)
                    probs = matrix_probs(build_matrix(lh, la, "baseline"))
                    acc = ext_blend["weights"][f"{w:.1f}"]
                    acc["log_loss"] += log_loss(probs, row["home_score"], row["away_score"])
                    acc["n"] += 1

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
    report["external_elo_blend"] = build_external_report(external_elo, ext_blend)
    report["market_blend"] = build_market_report()
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


def build_external_report(external_elo, ext_blend):
    """Reporte del blend de Elo externo sobre su subconjunto elegible."""
    n = ext_blend["baseline_subset"]["n"]
    if not external_elo or not n:
        return {
            "evaluable": False,
            "reason": "Falta data/elo_world.json o no hay partidos con ambos equipos rateados.",
            "weights_requested": ELO_BLEND_WEIGHTS,
        }
    base_subset = ext_blend["baseline_subset"]["log_loss"] / n
    weights = {}
    best_weight = None
    best_ll = None
    for w in ELO_BLEND_WEIGHTS:
        acc = ext_blend["weights"][f"{w:.1f}"]
        ll = acc["log_loss"] / acc["n"] if acc["n"] else None
        weights[f"{w:.1f}"] = {
            "log_loss": round(ll, 6) if ll is not None else None,
            "delta_vs_subset_baseline": round(ll - base_subset, 6) if ll is not None else None,
        }
        if ll is not None and (best_ll is None or ll < best_ll):
            best_ll = ll
            best_weight = w
    beats_subset = best_ll is not None and best_ll < base_subset
    return {
        "evaluable": True,
        "leakage_warning": (
            "Elo externo es un snapshot actual, no serie historica: usarlo sobre "
            "partidos pasados mete look-ahead bias que FAVORECE al blend. Solo un "
            "fracaso en superar el baseline del subconjunto es concluyente."
        ),
        "subset_matches": n,
        "baseline_subset_log_loss": round(base_subset, 6),
        "weights": weights,
        "best_weight": best_weight,
        "best_log_loss": round(best_ll, 6) if best_ll is not None else None,
        "beats_subset_baseline_with_leakage": beats_subset,
        "adopt": False,
        "adopt_reason": (
            "No se adopta: aun superando el baseline del subconjunto, el resultado "
            "no es concluyente por el look-ahead bias del snapshot."
            if beats_subset else
            "No se adopta: ni siquiera con leakage favorable supera el baseline del "
            "subconjunto, asi que el Elo externo no aporta."
        ),
    }


def build_market_report():
    """El mercado (odds.json) no es backtesteable: partidos solo futuros."""
    path = DATA / "odds.json"
    n_odds = 0
    if path.exists():
        n_odds = len(json.loads(path.read_text(encoding="utf-8")).get("odds", {}))
    return {
        "evaluable": False,
        "weights_requested": ODDS_BLEND_WEIGHTS,
        "odds_matches_available": n_odds,
        "historical_overlap_matches": 0,
        "reason": (
            "data/odds.json solo contiene partidos futuros del Mundial 2026 (claves "
            "tipo 2026-X-NN): cero solapamiento con el historial. No se puede medir "
            "mejora de log-loss historica del mercado."
        ),
        "adopt": False,
    }


# ---------------------------------------------------------------------------
# Sweep de hiperparametros (busqueda por coordenadas, validado train/test).
# Todos los parametros barridos son portables al modelo de produccion
# (predict.py / build_profiles.py / web/lib/model.ts).
# ---------------------------------------------------------------------------

TRAIN_END = date(2025, 1, 1)  # TRAIN: [2022-01-01, 2025-01-01); TEST: [2025-01-01, ...)

SWEEP_GRID = {
    "home_adv": [65.0, 75.0, 85.0, 95.0, 105.0],
    "base_total": [2.35, 2.45, 2.55, 2.65, 2.75],
    "rho": [1.00, 1.05, 1.10, 1.15, 1.20],
    "blend_w": [0.3, 0.4, 0.5, 0.6, 0.7],
}
BASE_CONFIG = {
    "home_adv": 85.0,
    "base_total": 2.55,
    "rho": 1.10,
    "blend_w": 0.5,
    "use_dc": False,
    "rho_dc": RHO_DC,
    "half_life": None,  # None => promedio simple (modelo actual)
}
ADOPT_MARGIN = 0.001  # margen minimo de mejora en log-loss global para adoptar


def apply_match_cfg(elo, home, away, home_score, away_score, tournament, neutral, home_adv):
    eh, ea = elo[home], elo[away]
    diff = eh - ea + (0.0 if neutral else home_adv)
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


def profile_cfg(team, elo, recent, as_of, half_life, global_gf, global_gc):
    rows = recent_records(recent[team], as_of)
    if half_life is None:
        avg_gf = simple_average(rows, "gf")
        avg_gc = simple_average(rows, "gc")
    else:
        avg_gf, n = weighted_average_hl(rows, as_of, "gf", half_life)
        avg_gc, _ = weighted_average_hl(rows, as_of, "gc", half_life)
        avg_gf = shrink(avg_gf, n, global_gf)
        avg_gc = shrink(avg_gc, n, global_gc)
    return {"elo": elo[team], "avg_gf_2y": avg_gf, "avg_gc_2y": avg_gc}


def weighted_average_hl(records, as_of, key, half_life):
    if not records:
        return 0.0, 0
    weighted_sum = 0.0
    total_weight = 0.0
    for record in records:
        days = max(0, (as_of - record["date"]).days)
        weight = 0.5 ** (days / half_life)
        weighted_sum += record[key] * weight
        total_weight += weight
    return (weighted_sum / total_weight if total_weight else 0.0), len(records)


def lambdas_cfg(home_profile, away_profile, neutral, home_adv, base_total, blend_w):
    diff = home_profile["elo"] - away_profile["elo"] + (0.0 if neutral else home_adv)
    we = elo_we(diff)
    attack = (
        home_profile["avg_gf_2y"] + away_profile["avg_gc_2y"]
        + away_profile["avg_gf_2y"] + home_profile["avg_gc_2y"]
    ) / 2.0
    total = max(1.8, min(3.6, blend_w * base_total + (1.0 - blend_w) * attack))
    return max(MIN_LAMBDA, total * we), max(MIN_LAMBDA, total * (1.0 - we))


def build_matrix_cfg(lambda_home, lambda_away, rho, use_dc, rho_dc):
    home = [poisson_pmf(lambda_home, i) for i in range(MAX_G + 1)]
    away = [poisson_pmf(lambda_away, j) for j in range(MAX_G + 1)]
    matrix = []
    for i in range(MAX_G + 1):
        row = []
        for j in range(MAX_G + 1):
            value = home[i] * away[j]
            if use_dc:
                value *= max(0.05, dixon_coles_tau(i, j, lambda_home, lambda_away, rho_dc))
            elif i == j:
                value *= rho
            row.append(value)
        matrix.append(row)
    total = sum(sum(row) for row in matrix)
    return [[value / total for value in row] for row in matrix]


def evaluate_config(rows, cfg):
    """Replay rolling completo para una config. Devuelve log-loss full/train/test."""
    elo = defaultdict(lambda: START_ELO)
    recent = defaultdict(list)
    global_goals = {"gf": 0.0, "gc": 0.0, "n": 0}
    buckets = {"full": [0.0, 0], "train": [0.0, 0], "test": [0.0, 0]}
    ha = cfg["home_adv"]
    for row in rows:
        home, away = row["home"], row["away"]
        if row["date"] >= BACKTEST_START:
            if global_goals["n"]:
                g_gf = global_goals["gf"] / global_goals["n"]
                g_gc = global_goals["gc"] / global_goals["n"]
            else:
                g_gf = g_gc = cfg["base_total"] / 2.0
            hp = profile_cfg(home, elo, recent, row["date"], cfg["half_life"], g_gf, g_gc)
            ap = profile_cfg(away, elo, recent, row["date"], cfg["half_life"], g_gf, g_gc)
            lh, la = lambdas_cfg(hp, ap, row["neutral"], ha, cfg["base_total"], cfg["blend_w"])
            probs = matrix_probs(build_matrix_cfg(lh, la, cfg["rho"], cfg["use_dc"], cfg["rho_dc"]))
            ll = log_loss(probs, row["home_score"], row["away_score"])
            buckets["full"][0] += ll
            buckets["full"][1] += 1
            tag = "train" if row["date"] < TRAIN_END else "test"
            buckets[tag][0] += ll
            buckets[tag][1] += 1
        apply_match_cfg(elo, home, away, row["home_score"], row["away_score"],
                        row["tournament"], row["neutral"], ha)
        recent[home].append({"date": row["date"], "gf": row["home_score"], "gc": row["away_score"]})
        recent[away].append({"date": row["date"], "gf": row["away_score"], "gc": row["home_score"]})
        global_goals["gf"] += row["home_score"] + row["away_score"]
        global_goals["gc"] += row["away_score"] + row["home_score"]
        global_goals["n"] += 2
    return {k: (s / n if n else None) for k, (s, n) in buckets.items()}


def run_sweep(rows):
    base = evaluate_config(rows, BASE_CONFIG)
    best_cfg = dict(BASE_CONFIG)
    best = evaluate_config(rows, best_cfg)
    history = [{"cfg": {k: best_cfg[k] for k in SWEEP_GRID}, "full": round(best["full"], 6),
                "train": round(best["train"], 6), "test": round(best["test"], 6)}]
    # busqueda por coordenadas: 2 pasadas
    for _ in range(2):
        for param, values in SWEEP_GRID.items():
            for value in values:
                if value == best_cfg[param]:
                    continue
                trial = dict(best_cfg)
                trial[param] = value
                res = evaluate_config(rows, trial)
                history.append({"cfg": {k: trial[k] for k in SWEEP_GRID},
                                "full": round(res["full"], 6),
                                "train": round(res["train"], 6),
                                "test": round(res["test"], 6)})
                if res["train"] < best["train"]:  # se optimiza por TRAIN
                    best, best_cfg = res, trial
    # variantes aisladas desde la mejor config numerica
    isolated = {}
    dc_cfg = dict(best_cfg); dc_cfg["use_dc"] = True
    isolated["+dixon_coles"] = {"cfg_delta": "use_dc=True", **_short(evaluate_config(rows, dc_cfg))}
    decay_cfg = dict(best_cfg); decay_cfg["half_life"] = HALF_LIFE_DAYS
    isolated["+time_decay"] = {"cfg_delta": f"half_life={HALF_LIFE_DAYS}",
                               **_short(evaluate_config(rows, decay_cfg))}

    improves_full = best["full"] < base["full"] - ADOPT_MARGIN
    holds_test = best["test"] < base["test"]
    adopt = improves_full and holds_test
    return {
        "method": "coordinate descent (2 pasadas), optimizado por log-loss TRAIN",
        "train_window": f"[{BACKTEST_START.isoformat()}, {TRAIN_END.isoformat()})",
        "test_window": f"[{TRAIN_END.isoformat()}, ...)",
        "grid": SWEEP_GRID,
        "baseline": _short(base),
        "best": {"cfg": {k: best_cfg[k] for k in SWEEP_GRID}, **_short(best)},
        "isolated_variants": isolated,
        "delta_full_vs_baseline": round(best["full"] - base["full"], 6),
        "delta_test_vs_baseline": round(best["test"] - base["test"], 6),
        "adopt": adopt,
        "adopt_reason": (
            f"Adoptar: la mejor config baja el log-loss global en "
            f"{round(base['full'] - best['full'], 6)} (>= margen {ADOPT_MARGIN}) y la mejora "
            f"se sostiene en TEST."
            if adopt else
            "No adoptar: la mejora no supera el margen minimo en el log-loss global "
            "y/o no se sostiene en el split TEST. El modelo ya esta en la frontera."
        ),
        "trials": history,
    }


def _short(res):
    return {"full": round(res["full"], 6), "train": round(res["train"], 6),
            "test": round(res["test"], 6)}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Ruta de salida alternativa")
    parser.add_argument("--no-sweep", action="store_true", help="Saltear el sweep de hiperparametros")
    args = parser.parse_args(argv)
    out_path = Path(args.output) if args.output else OUT

    if not (DATA / "history.csv").exists():
        print("Falta data/history.csv: corre fetch_history.py primero")
        return 1
    result = evaluate()
    if not args.no_sweep:
        result["results"]["hyperparam_sweep"] = run_sweep(read_history())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    res = result["results"]
    baseline = res["baseline"]["log_loss"]
    candidate = res["v2_candidate"]["log_loss"]
    decision = res["decision"]
    print(f"Backtest baseline log-loss: {baseline}")
    print(f"Backtest v2 candidate log-loss: {candidate} (delta {decision['delta_log_loss']})")
    print(f"Adoptar v2: {decision['adopt_v2']}")

    ext = res["external_elo_blend"]
    if ext.get("evaluable"):
        print(f"\nElo externo (subconjunto de {ext['subset_matches']} partidos, baseline {ext['baseline_subset_log_loss']}):")
        for w, info in ext["weights"].items():
            print(f"  peso {w}: log-loss {info['log_loss']} (delta {info['delta_vs_subset_baseline']})")
        print(f"  mejor peso: {ext['best_weight']} -> {ext['best_log_loss']}")
        print(f"  adoptar Elo externo: {ext['adopt']} ({ext['adopt_reason']})")
    else:
        print(f"\nElo externo: no evaluable ({ext.get('reason')})")

    mkt = res["market_blend"]
    print(f"\nMercado (odds): no evaluable. {mkt['reason']}")
    print(f"  pesos solicitados: {mkt['weights_requested']}; solapamiento historico: {mkt['historical_overlap_matches']}")

    sweep = res.get("hyperparam_sweep")
    if sweep:
        b = sweep["baseline"]
        best = sweep["best"]
        print(f"\nSweep de hiperparametros ({sweep['method']}):")
        print(f"  baseline:  full {b['full']} | train {b['train']} | test {b['test']}")
        print(f"  mejor cfg: {best['cfg']}")
        print(f"             full {best['full']} | train {best['train']} | test {best['test']}")
        for name, info in sweep["isolated_variants"].items():
            print(f"  {name} ({info['cfg_delta']}): full {info['full']} | test {info['test']}")
        print(f"  delta full vs baseline: {sweep['delta_full_vs_baseline']} | delta test: {sweep['delta_test_vs_baseline']}")
        print(f"  ADOPTAR: {sweep['adopt']} -> {sweep['adopt_reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
