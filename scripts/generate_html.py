# -*- coding: utf-8 -*-
"""Regenera mundial2026.html desde data/*.json con la plantilla Jinja2.

La version manual original se preserva una sola vez como mundial2026.manual.html.
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).parent))
from teams import GROUPS, ES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "mundial2026.html"
BACKUP = ROOT / "mundial2026.manual.html"

GROUP_COLORS = {"A": "#dc2626", "B": "#ea580c", "C": "#16a34a", "D": "#2563eb",
                "E": "#7c3aed", "F": "#db2777", "G": "#0d9488", "H": "#ca8a04",
                "I": "#4f46e5", "J": "#0891b2", "K": "#9333ea", "L": "#b91c1c"}
WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
WD_SHORT = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MONTHS_ES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
             "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def matchday(date_str):
    if date_str <= "2026-06-17":
        return "Fecha 1", ""
    if date_str <= "2026-06-23":
        return "Fecha 2", "f2"
    return "Fecha 3", "f3"


def short_venue(v):
    v = re.sub(r"\s+", " ", v or "").strip()
    return v[:48] + ("…" if len(v) > 48 else "")


def form_str(wdl):
    return f"{wdl[0]}G-{wdl[1]}E-{wdl[2]}P"


def main():
    fx = json.loads((DATA / "fixture.json").read_text(encoding="utf-8"))
    pj = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))
    sim = json.loads((DATA / "simulation.json").read_text(encoding="utf-8"))
    profs = json.loads((DATA / "team_profiles.json").read_text(encoding="utf-8"))
    preds, profiles = pj["predictions"], profs["profiles"]

    # backup de la version manual (una sola vez)
    if OUT.exists() and not BACKUP.exists():
        shutil.copy2(OUT, BACKUP)
        print(f"Backup de la version manual -> {BACKUP.name}")

    # ---- dias ----
    by_day = {}
    for m in fx["matches"]:
        by_day.setdefault(m["date"] or "9999-99-99", []).append(m)

    days = []
    for date_str in sorted(by_day):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            wd, wds = WEEKDAYS[dt.weekday()], WD_SHORT[dt.weekday()]
            title = f"{wd} {dt.day} de {MONTHS_ES[dt.month]}"
            short = f"{wds} {dt.day}"
            anchor = f"{dt.day:02d}"
        except ValueError:
            title, short, anchor = date_str, date_str, "x"
        md_label, md_class = matchday(date_str)
        ms = []
        for m in sorted(by_day[date_str], key=lambda x: (x["time"] or "99", x["group"])):
            played = m["status"] == "played"
            card = {
                "group": m["group"], "played": played,
                "home": m["home_es"], "away": m["away_es"],
                "meta": f"{m['time'] or ''} · {short_venue(m['venue'])}".strip(" ·"),
            }
            if played:
                card["score"] = f"{m['score'][0]} - {m['score'][1]}"
                ph, pa = profiles[m["home"]], profiles[m["away"]]
                card["comment"] = f"Elo post: {ph['elo']:.0f} vs {pa['elo']:.0f}"
                card["star"] = False
                card["dificil"] = False
            else:
                p = preds[m["match_id"]]
                card.update({
                    "score": f"{p['score_pred'][0]} - {p['score_pred'][1]}",
                    "p1": p["p1"], "px": p["px"], "p2": p["p2"],
                    "conf": p["confidence"],
                    "conf_class": {"alta": "alta", "media-alta": "media",
                                   "media": "media", "baja": "baja"}[p["confidence"]],
                    "star": min(p["elo_home"], p["elo_away"]) >= 1900,
                    "dificil": p["confidence"] == "baja",
                })
                fh = form_str(profiles[m["home"]]["form_last10"])
                fa = form_str(profiles[m["away"]]["form_last10"])
                card["comment"] = (f"Elo {p['elo_home']:.0f} vs {p['elo_away']:.0f} "
                                   f"(Δ{p['elo_diff']:+.0f}{', localía' if p['host_home'] else ''}) · "
                                   f"forma {fh} vs {fa}")
            ms.append(card)
        days.append({"anchor": anchor, "short": short, "title": title,
                     "subtitle": f"{len(ms)} partido{'s' if len(ms) != 1 else ''}",
                     "md_label": md_label, "md_class": md_class, "matches": ms})

    # ---- tablas por grupo ----
    steams = sim["teams"]
    groups_ctx = []
    for g, ts in GROUPS.items():
        ranked = sorted(ts, key=lambda t: -steams[t]["exp_pts"])
        rows = []
        for i, t in enumerate(ranked):
            s = steams[t]
            rows.append({
                "name": ES[t], "exp_pts": f"{s['exp_pts']:.1f}",
                "exp_gd": f"{s['exp_gd']:+.1f}", "p_first": f"{s['p_first']:.0f}",
                "p_advance": f"{s['p_advance']:.0f}",
                "row_class": "q1" if i < 2 else ("q3" if i == 2 else ""),
            })
        groups_ctx.append({"letter": g, "color": GROUP_COLORS[g], "teams": rows})

    # ---- terceros: el mas probable de cada grupo ----
    thirds = []
    for g, ts in GROUPS.items():
        t = max(ts, key=lambda x: steams[x]["p_third"])
        s = steams[t]
        thirds.append({"name": ES[t], "group": g,
                       "p_third": f"{s['p_third']:.0f}",
                       "p_third_qualify": f"{s['p_third_qualify']:.0f}",
                       "p_advance": f"{s['p_advance']:.0f}",
                       "_q": s["p_third_qualify"]})
    thirds.sort(key=lambda x: -x["_q"])
    for i, t in enumerate(thirds):
        t["likely"] = i < 8

    played_count = sum(1 for m in fx["matches"] if m["status"] == "played")
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=False)
    html = env.get_template("mundial.html.j2").render(
        updated=fx["updated"].replace("T", " "),
        n_sims=sim["n_sims"],
        n_history=profs["history_matches_used"],
        played_count=played_count,
        pending_count=len(fx["matches"]) - played_count,
        arg_advance=f"{steams['Argentina']['p_advance']:.0f}",
        days=days, groups=groups_ctx, thirds=thirds,
        model_desc=pj["model"],
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"OK {OUT.name} regenerado ({len(html)//1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
