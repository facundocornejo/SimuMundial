# -*- coding: utf-8 -*-
"""Genera prode.html: formulario autocontenido para que cada jugador cargue
sus 72 pronosticos y exporte su archivo prode_<nombre>.json.

TODOS los partidos son editables, incluso los ya jugados (sirve para
transcribir pronosticos hechos antes del torneo; sistema de confianza).
El resultado real se muestra al lado como referencia.
"""
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "prode.html"


def main():
    fx = json.loads((DATA / "fixture.json").read_text(encoding="utf-8"))
    pj = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))["predictions"]
    picks_path = DATA / "model_picks.json"
    model_picks = json.loads(picks_path.read_text(encoding="utf-8")) if picks_path.exists() else {}

    payload = []
    for m in fx["matches"]:
        mid = m["match_id"]
        model = pj[mid]["score_pred"] if mid in pj else model_picks.get(mid)
        payload.append({
            "id": mid, "g": m["group"], "d": m["date"],
            "h": m["home_es"], "a": m["away_es"],
            "hc": m["home"], "ac": m["away"],
            "played": m["status"] == "played",
            "score": m["score"],
            "model": model,
        })

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    html = env.get_template("prode.html.j2").render(
        matches_json=json.dumps(payload, ensure_ascii=False),
        updated=fx["updated"].replace("T", " "),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"OK prode.html generado ({len(payload)} partidos, "
          f"{sum(1 for m in payload if m['played'])} bloqueados)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
