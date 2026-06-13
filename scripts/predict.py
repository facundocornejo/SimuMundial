# -*- coding: utf-8 -*-
"""Modelo de prediccion: Elo -> Poisson con inflacion de empate.

Para cada partido pendiente:
  - dElo = elo_home - elo_away (+85 si un anfitrion juega en su pais)
  - We   = prob. esperada Elo
  - total de goles esperado segun ataque/defensa recientes de ambos
  - lambda_home / lambda_away reparten ese total segun We
  - matriz Poisson 0-8 x 0-8 con diagonal inflada (rho) -> p1/px/p2 + marcador modal

Salida: data/predictions.json
"""
import json
import math
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# Constantes del modelo calibradas por backtest (sweep validado train/test) 2026-06-13.
# SYNC: web/lib/model.ts y build_profiles.py (HOME_ADV) deben coincidir.
HOME_ADV = 75.0
RHO = 1.15          # inflacion del empate (Dixon-Coles simplificado)
MAX_G = 8
MIN_LAMBDA = 0.18
BASE_TOTAL = 2.35   # goles por partido de referencia en Mundiales
TOTAL_BLEND_W = 0.7  # peso del total base vs ataque reciente al repartir goles

# Blend con el mercado: las predicciones mostradas de partidos con cuota se mezclan
# hacia las casas de apuestas (predictor mejor calibrado segun la literatura).
# No es backtesteable (no hay serie historica de cuotas); justificacion: evidencia
# de que el mercado supera a cualquier modelo en calibracion. Reversible con 0.0.
MARKET_BLEND_W = 0.40  # 60% modelo / 40% mercado


def elo_we(diff):
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


def poisson_pmf(lmb, k):
    return math.exp(-lmb) * lmb ** k / math.factorial(k)


def lambdas(p_home, p_away, host_home):
    diff = p_home["elo"] - p_away["elo"] + (HOME_ADV if host_home else 0.0)
    we = elo_we(diff)
    # total esperado: mezcla del baseline mundialista con ataque/defensa recientes
    atk = (p_home["avg_gf_2y"] + p_away["avg_gc_2y"]
           + p_away["avg_gf_2y"] + p_home["avg_gc_2y"]) / 2.0
    total = max(1.8, min(3.6, TOTAL_BLEND_W * BASE_TOTAL + (1.0 - TOTAL_BLEND_W) * atk))
    lh = max(MIN_LAMBDA, total * we)
    la = max(MIN_LAMBDA, total * (1.0 - we))
    return lh, la, diff, we


def build_matrix(lh, la, rho=RHO, max_g=MAX_G):
    """Matriz de prob. de marcadores con diagonal inflada y renormalizada."""
    ph = [poisson_pmf(lh, i) for i in range(max_g + 1)]
    pa = [poisson_pmf(la, j) for j in range(max_g + 1)]
    mat = [[ph[i] * pa[j] * (rho if i == j else 1.0)
            for j in range(max_g + 1)] for i in range(max_g + 1)]
    s = sum(sum(r) for r in mat)
    return [[v / s for v in row] for row in mat]


def matrix_summary(mat):
    p1 = sum(mat[i][j] for i in range(len(mat)) for j in range(len(mat)) if i > j)
    px = sum(mat[i][i] for i in range(len(mat)))
    p2 = 1.0 - p1 - px
    best = max(((i, j) for i in range(len(mat)) for j in range(len(mat))),
               key=lambda ij: mat[ij[0]][ij[1]])
    over25 = sum(mat[i][j] for i in range(len(mat)) for j in range(len(mat)) if i + j >= 3)
    return p1, px, p2, best, over25


def round_to_100(p1, px, p2):
    """Redondeo por restos mayores: enteros que suman exactamente 100."""
    raw = [p1 * 100, px * 100, p2 * 100]
    floors = [int(x) for x in raw]
    rest = 100 - sum(floors)
    order = sorted(range(3), key=lambda i: raw[i] - floors[i], reverse=True)
    for i in range(rest):
        floors[order[i]] += 1
    return floors


def confidence(maxp):
    if maxp >= 70:
        return "alta"
    if maxp >= 55:
        return "media-alta"
    if maxp >= 45:
        return "media"
    return "baja"


def load_market_odds():
    path = DATA / "odds.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("odds", {})


def favorite_of(home, away, i1, ix, i2):
    """Devuelve (favorito, condicion de marcador) segun probabilidades enteras."""
    maxp = max(i1, ix, i2)
    if i1 == maxp and i1 >= i2:
        return home, (lambda i, j: i > j), maxp
    if i2 == maxp:
        return away, (lambda i, j: i < j), maxp
    return "empate", (lambda i, j: i == j), maxp


def main():
    fx = json.loads((DATA / "fixture.json").read_text(encoding="utf-8"))
    profs = json.loads((DATA / "team_profiles.json").read_text(encoding="utf-8"))["profiles"]
    odds = load_market_odds()

    preds = {}
    blended = []
    for m in fx["matches"]:
        if m["status"] == "played":
            continue
        ph, pa = profs[m["home"]], profs[m["away"]]
        host_home = (m["home"] == m["venue_country"])
        lh, la, diff, we = lambdas(ph, pa, host_home)
        mat = build_matrix(lh, la)
        p1, px, p2, best, over25 = matrix_summary(mat)

        # Marcador modal SIEMPRE del modelo puro (lo que se congela en model_picks).
        m1, mx, m2 = round_to_100(p1, px, p2)
        _, model_cond, _ = favorite_of(m["home"], m["away"], m1, mx, m2)
        rng = range(len(mat))
        pred = list(max(((i, j) for i in rng for j in rng if model_cond(i, j)),
                        key=lambda ij: mat[ij[0]][ij[1]]))

        # Probabilidades MOSTRADAS: blend hacia el mercado si hay cuota disponible.
        mk = odds.get(m["match_id"])
        if mk and MARKET_BLEND_W > 0:
            s = mk["p1"] + mk["px"] + mk["p2"]
            if s > 0:
                w = MARKET_BLEND_W
                p1 = (1 - w) * p1 + w * (mk["p1"] / s)
                px = (1 - w) * px + w * (mk["px"] / s)
                p2 = (1 - w) * p2 + w * (mk["p2"] / s)
                blended.append(m["match_id"])

        i1, ix, i2 = round_to_100(p1, px, p2)
        fav, _, maxp = favorite_of(m["home"], m["away"], i1, ix, i2)
        preds[m["match_id"]] = {
            "p1": i1, "px": ix, "p2": i2,
            "lambda_home": round(lh, 3), "lambda_away": round(la, 3),
            "rho": RHO,
            "elo_home": ph["elo"], "elo_away": pa["elo"],
            "elo_diff": round(diff, 1), "host_home": host_home,
            "score_pred": pred,
            "over25": round(over25 * 100),
            "favorite": fav,
            "confidence": confidence(maxp),
        }

    out = {"updated": datetime.now().isoformat(timespec="seconds"),
           "model": "Elo->Poisson rho=%.2f, home_adv=%.0f" % (RHO, HOME_ADV),
           "market_blend": {"weight": MARKET_BLEND_W, "matches_blended": len(blended)},
           "predictions": preds}
    with open(DATA / "predictions.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # sanity check
    for mid, p in preds.items():
        assert p["p1"] + p["px"] + p["p2"] == 100, f"{mid} no suma 100"
    print(f"OK predictions.json: {len(preds)} partidos pendientes modelados"
          f" ({len(blended)} con blend de mercado al {int(MARKET_BLEND_W*100)}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
