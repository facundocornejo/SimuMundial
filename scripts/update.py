# -*- coding: utf-8 -*-
"""Orquestador: corre todo el pipeline en orden y valida.

Uso:
  python scripts/update.py                 # todo
  python scripts/update.py --skip-history  # sin re-bajar el CSV historico
  python scripts/update.py --no-html       # sin regenerar el HTML
"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
WEB_DATA = ROOT / "web" / "data"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run(name, fn, *args):
    print(f"\n=== {name} ===")
    rc = fn(*args)
    if rc not in (0, None):
        print(f"FALLO en {name} (rc={rc})")
        sys.exit(rc)


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


def validate():
    print("\n=== Validacion ===")
    fx = json.loads((DATA / "fixture.json").read_text(encoding="utf-8"))
    assert len(fx["matches"]) == 72, f"fixture: {len(fx['matches'])} != 72 partidos"
    played = [m for m in fx["matches"] if m["status"] == "played"]
    assert played, "fixture: no hay ningun partido jugado (deberia estar Mexico-Sudafrica)"

    pj = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))["predictions"]
    for mid, p in pj.items():
        assert p["p1"] + p["px"] + p["p2"] == 100, f"{mid}: probabilidades no suman 100"

    profs = json.loads((DATA / "team_profiles.json").read_text(encoding="utf-8"))["profiles"]
    assert len(profs) == 48, f"profiles: {len(profs)} != 48 equipos"

    sim = json.loads((DATA / "simulation.json").read_text(encoding="utf-8"))["teams"]
    for g in "ABCDEFGHIJKL":
        tot = sum(t["p_first"] for t in sim.values() if t["group"] == g)
        assert 99.0 <= tot <= 101.0, f"grupo {g}: P(1ro) suma {tot}"

    # sanity: favoritos obvios
    def fav_prob(home, away):
        for m in fx["matches"]:
            if m["home"] == home and m["away"] == away and m["status"] == "pending":
                return pj[m["match_id"]]["p1"]
        return None
    for h, a, floor in (("Spain", "Cape Verde", 70), ("Argentina", "Algeria", 60)):
        p = fav_prob(h, a)
        if p is not None:
            assert p >= floor, f"sanity: {h} vs {a} dio {p}% (< {floor}%) - revisar signo dElo"
            print(f"  sanity {h} vs {a}: {p}% OK")
    print("  Validacion OK: 72 partidos, ternas=100, 48 Elo, sims consistentes")


def copy_web_data():
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    for name in ("fixture.json", "team_profiles.json", "predictions.json", "model_picks.json"):
        shutil.copy2(DATA / name, WEB_DATA / name)
    print("  Datos copiados a web/data")


def main():
    load_env_file()
    args = sys.argv[1:]
    import fetch_fixture, fetch_history, fetch_rankings, fetch_elo, fetch_odds
    import build_profiles, predict, simulate, generate_html
    import generate_prode, game

    run("1/9 Fixture y resultados", fetch_fixture.main)
    if "--skip-history" not in args:
        run("2/9 Historico internacional", fetch_history.main, "--force" in args)
    run("3/9 Ranking FIFA", fetch_rankings.main)
    fetcher_args = ["--force"] if "--force" in args else []
    run("3b/9 Elo externo", fetch_elo.main, fetcher_args)
    run("3c/9 Cuotas", fetch_odds.main, fetcher_args)
    run("4/9 Elo + perfiles", build_profiles.main)
    run("5/9 Modelo de prediccion", predict.main)
    run("6/9 Monte Carlo", simulate.main)
    if "--no-html" not in args:
        run("7/9 HTML analisis", generate_html.main)
        run("8/9 Formulario prode", generate_prode.main)
        run("9/9 El juego", game.main)
    validate()
    run("10/10 Datos web app", copy_web_data)
    print("\nPipeline completo. Abri mundial2026.html o corré la web app para ver el resultado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
