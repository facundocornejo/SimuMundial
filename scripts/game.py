# -*- coding: utf-8 -*-
"""PARTE 2 - El juego: lee los prodes de prode/*.json, y para cada jugador:
  1. Toma SUS resultados de fase de grupos (incluso de partidos ya jugados:
     sirve para transcribir pronosticos hechos antes del torneo).
  2. Arma su cuadro de 16avos con el bracket oficial FIFA.
  3. "Adivina" las fases siguientes hasta la final SORTEANDO cada cruce con
     las probabilidades del modelo Elo->Poisson (estadistica + azar).
     El sorteo usa una semilla fija derivada del nombre + su prode, asi el
     destino de cada jugador es unico pero NO cambia entre regeneraciones.
  4. Puntua contra los resultados reales a medida que se juegan.

Puntaje:
  - Resultado exacto: 3 pts | Acierto 1X2: 1 pt (todos los partidos jugados)
  - Bonus al cerrar grupos: +2 por clasificado real acertado entre los 32
  - Bonus final: +10 si tu campeon "sorteado" sale campeon real
El jugador "Modelo" puntua con sus predicciones pre-partido congeladas en
data/model_picks.json (no se pisan cuando el partido ya se jugo).

Uso: python scripts/game.py
"""
import hashlib
import json
import random
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
from teams import ES
from bracket import R16, QF, SF, FINAL, build_r32
from predict import build_matrix, matrix_summary, BASE_TOTAL, MIN_LAMBDA

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PRODE = ROOT / "prode"
OUT = ROOT / "juego.html"

PTS_EXACT, PTS_OUTCOME, PTS_QUALIFIED, PTS_CHAMPION = 3, 1, 2, 10
HOME_ADV = 85.0
MAX_G = 8


def ko_matrix(home, away, country, profiles):
    """Matriz de marcadores (90') + prob. Elo del local para alargue/penales."""
    ph, pa = profiles[home], profiles[away]
    diff = (ph["elo"] - pa["elo"]
            + (HOME_ADV if home == country else 0.0)
            - (HOME_ADV if away == country else 0.0))
    we = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
    atk = (ph["avg_gf_2y"] + pa["avg_gc_2y"] + pa["avg_gf_2y"] + ph["avg_gc_2y"]) / 2.0
    total = max(1.8, min(3.6, 0.5 * BASE_TOTAL + 0.5 * atk))
    lh = max(MIN_LAMBDA, total * we)
    la = max(MIN_LAMBDA, total * (1.0 - we))
    return build_matrix(lh, la), we


def ko_draw(home, away, country, profiles, rng):
    """Sortea un cruce eliminatorio: marcador muestreado de la matriz; si da
    empate, alargue/penales se definen con la prob. Elo. Devuelve
    (ganador, marcador_str, prob_del_ganador, fue_penales)."""
    mat, we = ko_matrix(home, away, country, profiles)
    p1, px, p2, _, _ = matrix_summary(mat)
    pwin_h = p1 + px * we

    r = rng.random()
    acc = 0.0
    hs = as_ = 0
    for i in range(MAX_G + 1):
        for j in range(MAX_G + 1):
            acc += mat[i][j]
            if r <= acc:
                hs, as_ = i, j
                break
        else:
            continue
        break

    pens = hs == as_
    if pens:
        winner = home if rng.random() < we else away
        score = f"{hs}-{as_} (pen)"
    else:
        winner = home if hs > as_ else away
        score = f"{hs}-{as_}"
    pwin = pwin_h if winner == home else 1.0 - pwin_h
    return winner, score, round(100 * pwin), pens


def run_knockout(r32_fixtures, profiles, rng):
    """Sortea 16avos -> final con el RNG del jugador."""
    winners = {}
    rounds = {"r32": [], "r16": [], "qf": [], "sf": [], "final": []}
    for f in r32_fixtures:
        w, score, p, pens = ko_draw(f["home"], f["away"], f["country"], profiles, rng)
        winners[f["n"]] = w
        rounds["r32"].append({**f, "winner": w, "score": score, "p": p})
    for key, defs in (("r16", R16), ("qf", QF), ("sf", SF)):
        for n, a, b, date, venue, country in defs:
            h, aw = winners[a], winners[b]
            w, score, p, pens = ko_draw(h, aw, country, profiles, rng)
            winners[n] = w
            rounds[key].append({"n": n, "home": h, "away": aw, "date": date,
                                "venue": venue, "winner": w, "score": score, "p": p})
    n, a, b, date, venue, country = FINAL
    h, aw = winners[a], winners[b]
    w, score, p, pens = ko_draw(h, aw, country, profiles, rng)
    rounds["final"].append({"n": n, "home": h, "away": aw, "date": date,
                            "venue": venue, "winner": w, "score": score, "p": p})
    return rounds, w


def player_rng(name, results):
    """Semilla deterministica: mismo prode -> mismo destino, siempre."""
    blob = name + json.dumps(results, sort_keys=True)
    seed = int(hashlib.md5(blob.encode("utf-8")).hexdigest(), 16) % (2 ** 32)
    return random.Random(seed)


def score_player(picks, real_matches):
    """Puntua todos los partidos reales jugados contra los picks."""
    exact = outcome = 0
    for m in real_matches:
        if m["status"] != "played":
            continue
        pick = picks.get(m["match_id"])
        if not pick:
            continue
        rs = m["score"]
        if list(pick) == list(rs):
            exact += 1
        else:
            sign = lambda s: 0 if s[0] == s[1] else (1 if s[0] > s[1] else -1)
            if sign(pick) == sign(rs):
                outcome += 1
    return exact, outcome


def update_model_picks(matches, preds):
    """Congela la prediccion del modelo de cada partido ANTES de que se juegue.
    Una vez grabada, no se pisa (es el pick 'historico' del modelo)."""
    path = DATA / "model_picks.json"
    picks = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    added = 0
    for m in matches:
        mid = m["match_id"]
        if m["status"] == "pending" and mid not in picks and mid in preds:
            picks[mid] = preds[mid]["score_pred"]
            added += 1
    path.write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    if added:
        print(f"  model_picks.json: {added} predicciones nuevas congeladas")
    return picks


def main():
    fx = json.loads((DATA / "fixture.json").read_text(encoding="utf-8"))
    profiles = json.loads((DATA / "team_profiles.json").read_text(encoding="utf-8"))["profiles"]
    preds = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))["predictions"]
    matches = fx["matches"]
    fairplay = fx.get("fairplay", {})
    real_played = {m["match_id"]: m["score"] for m in matches if m["status"] == "played"}

    model_picks = update_model_picks(matches, preds)

    # ---- jugadores ----
    PRODE.mkdir(exist_ok=True)
    entries = []
    for f in sorted(PRODE.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            entries.append({"player": d["player"], "results": d["results"], "file": f.name})
        except Exception as e:
            print(f"[aviso] {f.name} invalido: {e}")

    # jugador virtual: el modelo (sus picks congelados; lo pendiente, su prediccion actual)
    entries.append({"player": "🤖 Modelo", "results": dict(model_picks), "file": None})

    players = []
    for e in entries:
        picks = {mid: list(sc) for mid, sc in e["results"].items() if sc}
        # para armar el cuadro: lo real jugado pisa el pronostico
        full = dict(picks)
        full.update({mid: list(sc) for mid, sc in real_played.items()})
        if len(full) < len(matches):
            print(f"[aviso] {e['player']}: prode incompleto ({len(full)}/72), salteado")
            continue
        r32, ranked, table, thirds = build_r32(full, matches, fairplay)
        rng = player_rng(e["player"], picks)
        rounds, champion = run_knockout(r32, profiles, rng)
        exact, outcome = score_player(picks, matches)
        qualified = {f_["home"] for f_ in r32} | {f_["away"] for f_ in r32}
        finalists = [rounds["final"][0]["home"], rounds["final"][0]["away"]]
        players.append({
            "name": e["player"], "is_model": e["file"] is None,
            "exact": exact, "outcome": outcome,
            "points": exact * PTS_EXACT + outcome * PTS_OUTCOME,
            "champion": ES[champion],
            "final": f"{ES[finalists[0]]} vs {ES[finalists[1]]}",
            "final_score": rounds["final"][0]["score"],
            "group_winners": {g: ES[ranked[g][0]] for g in sorted(ranked)},
            "thirds": [ES[t] for t in thirds],
            "qualified": sorted(ES[t] for t in qualified),
            "rounds": {k: [{**r, "home": ES[r["home"]], "away": ES[r["away"]],
                            "winner": ES[r["winner"]]} for r in v]
                       for k, v in rounds.items()},
        })

    players.sort(key=lambda p: (-p["points"], -p["exact"], p["name"].lower()))

    played_count = len(real_played)
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    html = env.get_template("juego.html.j2").render(
        players=players,
        n_players=sum(1 for p in players if not p["is_model"]),
        played=played_count, pending=len(matches) - played_count,
        updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
        rules=dict(exact=PTS_EXACT, outcome=PTS_OUTCOME,
                   qualified=PTS_QUALIFIED, champion=PTS_CHAMPION),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"OK juego.html: {len(players)} participantes "
          f"({sum(1 for p in players if not p['is_model'])} humanos + modelo), "
          f"{played_count} partidos puntuados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
