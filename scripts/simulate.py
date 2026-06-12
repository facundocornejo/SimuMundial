# -*- coding: utf-8 -*-
"""Monte Carlo de la fase de grupos (10.000 corridas).

Partidos jugados: resultado real fijo. Pendientes: se muestrean de la matriz
de Poisson del modelo. Reglamento real: pts -> DG -> GF -> fair play -> azar;
clasifican 1, 2 y los 8 mejores terceros.

Salida: data/simulation.json
"""
import json
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from teams import GROUPS
from predict import build_matrix

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
N_SIMS = 10000
MAX_G = 8


def sample_score(flat, cum):
    r = random.random()
    lo, hi = 0, len(cum) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if cum[mid] < r:
            lo = mid + 1
        else:
            hi = mid
    return flat[lo]


def main(n_sims=N_SIMS):
    fx = json.loads((DATA / "fixture.json").read_text(encoding="utf-8"))
    pj = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))["predictions"]
    fairplay = fx.get("fairplay", {})  # deduccion (negativa = peor)

    # precomputo de distribuciones por partido pendiente
    dists = {}
    for m in fx["matches"]:
        if m["status"] == "played":
            continue
        p = pj[m["match_id"]]
        mat = build_matrix(p["lambda_home"], p["lambda_away"], p["rho"])
        flat, cum, acc = [], [], 0.0
        for i in range(MAX_G + 1):
            for j in range(MAX_G + 1):
                flat.append((i, j))
                acc += mat[i][j]
                cum.append(acc)
        cum[-1] = 1.0
        dists[m["match_id"]] = (flat, cum)

    teams = [t for g in GROUPS.values() for t in g]
    stats = {t: {"p1": 0, "p2": 0, "p3": 0, "p3q": 0, "out": 0,
                 "pts": 0.0, "gf": 0.0, "gc": 0.0} for t in teams}

    random.seed(20260612)
    for _ in range(n_sims):
        table = {t: [0, 0, 0] for t in teams}  # pts, gf, gc
        for m in fx["matches"]:
            if m["status"] == "played":
                hs, as_ = m["score"]
            else:
                hs, as_ = sample_score(*dists[m["match_id"]])
            h, a = m["home"], m["away"]
            table[h][1] += hs; table[h][2] += as_
            table[a][1] += as_; table[a][2] += hs
            if hs > as_:
                table[h][0] += 3
            elif hs < as_:
                table[a][0] += 3
            else:
                table[h][0] += 1; table[a][0] += 1

        thirds = []
        for g, ts in GROUPS.items():
            ranked = sorted(ts, key=lambda t: (
                -table[t][0], -(table[t][1] - table[t][2]), -table[t][1],
                -fairplay.get(t, 0), random.random()))
            stats[ranked[0]]["p1"] += 1
            stats[ranked[1]]["p2"] += 1
            stats[ranked[2]]["p3"] += 1
            stats[ranked[3]]["out"] += 1
            thirds.append(ranked[2])

        thirds.sort(key=lambda t: (
            -table[t][0], -(table[t][1] - table[t][2]), -table[t][1],
            -fairplay.get(t, 0), random.random()))
        for t in thirds[:8]:
            stats[t]["p3q"] += 1
        for t in thirds[8:]:
            stats[t]["out"] += 1

        for t in teams:
            stats[t]["pts"] += table[t][0]
            stats[t]["gf"] += table[t][1]
            stats[t]["gc"] += table[t][2]

    result = {}
    for t in teams:
        s = stats[t]
        adv = (s["p1"] + s["p2"] + s["p3q"]) / n_sims
        result[t] = {
            "group": [g for g, ts in GROUPS.items() if t in ts][0],
            "p_first": round(100 * s["p1"] / n_sims, 1),
            "p_second": round(100 * s["p2"] / n_sims, 1),
            "p_third": round(100 * s["p3"] / n_sims, 1),
            "p_third_qualify": round(100 * s["p3q"] / n_sims, 1),
            "p_advance": round(100 * adv, 1),
            "p_out": round(100 * (1 - adv), 1),
            "exp_pts": round(s["pts"] / n_sims, 2),
            "exp_gf": round(s["gf"] / n_sims, 2),
            "exp_gc": round(s["gc"] / n_sims, 2),
            "exp_gd": round((s["gf"] - s["gc"]) / n_sims, 2),
        }

    out = {"updated": datetime.now().isoformat(timespec="seconds"),
           "n_sims": n_sims, "teams": result}
    with open(DATA / "simulation.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # resumen por consola
    print(f"OK simulation.json ({n_sims} simulaciones)")
    for g, ts in GROUPS.items():
        ranked = sorted(ts, key=lambda t: -result[t]["exp_pts"])
        line = " | ".join(f"{t} {result[t]['exp_pts']:.1f}pts {result[t]['p_advance']:.0f}%"
                          for t in ranked)
        print(f"  {g}: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
