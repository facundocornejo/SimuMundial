# -*- coding: utf-8 -*-
"""Cuadro eliminatorio oficial del Mundial 2026 + utilidades del juego.

Estructura verificada en Wikipedia (knockout stage):
- 16avos (partidos 73-88): ganadores/segundos fijos + 8 terceros por cupos.
- La asignacion exacta de terceros usa el Anexo C de FIFA (495 combinaciones);
  aca se resuelve un emparejamiento valido por backtracking respetando los
  cupos oficiales de cada llave (nunca cruza a un tercero con el ganador de
  su propio grupo). Es una aproximacion fiel, no el Anexo C literal.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from teams import GROUPS

# (nro, slot_local, slot_visita, fecha, sede, pais_sede)
# slot: ("W","A")=ganador grupo A · ("R","B")=segundo B · ("T","ABCDF")=tercero de esos grupos
R32 = [
    (73, ("R", "A"), ("R", "B"), "28/6", "SoFi Stadium, Inglewood", "United States"),
    (74, ("W", "E"), ("T", "ABCDF"), "29/6", "Gillette Stadium, Boston", "United States"),
    (75, ("W", "F"), ("R", "C"), "29/6", "Estadio BBVA, Monterrey", "Mexico"),
    (76, ("W", "C"), ("R", "F"), "29/6", "NRG Stadium, Houston", "United States"),
    (77, ("W", "I"), ("T", "CDFGH"), "30/6", "MetLife Stadium, NY/NJ", "United States"),
    (78, ("R", "E"), ("R", "I"), "30/6", "AT&T Stadium, Dallas", "United States"),
    (79, ("W", "A"), ("T", "CEFHI"), "30/6", "Estadio Azteca, CDMX", "Mexico"),
    (80, ("W", "L"), ("T", "EHIJK"), "1/7", "Mercedes-Benz, Atlanta", "United States"),
    (81, ("W", "D"), ("T", "BEFIJ"), "1/7", "Levi's Stadium, Santa Clara", "United States"),
    (82, ("W", "G"), ("T", "AEHIJ"), "1/7", "Lumen Field, Seattle", "United States"),
    (83, ("R", "K"), ("R", "L"), "2/7", "BMO Field, Toronto", "Canada"),
    (84, ("W", "H"), ("R", "J"), "2/7", "SoFi Stadium, Inglewood", "United States"),
    (85, ("W", "B"), ("T", "EFGIJ"), "2/7", "BC Place, Vancouver", "Canada"),
    (86, ("W", "J"), ("R", "H"), "3/7", "Hard Rock, Miami", "United States"),
    (87, ("W", "K"), ("T", "DEIJL"), "3/7", "Arrowhead, Kansas City", "United States"),
    (88, ("R", "D"), ("R", "G"), "3/7", "AT&T Stadium, Dallas", "United States"),
]
R16 = [(89, 74, 77, "4/7", "Philadelphia", "United States"),
       (90, 73, 75, "4/7", "Houston", "United States"),
       (91, 76, 78, "5/7", "Estadio Azteca, CDMX", "Mexico"),
       (92, 79, 80, "5/7", "Dallas", "United States"),
       (93, 83, 84, "6/7", "Seattle", "United States"),
       (94, 81, 82, "6/7", "Atlanta", "United States"),
       (95, 86, 88, "7/7", "Vancouver", "Canada"),
       (96, 85, 87, "7/7", "Miami", "United States")]
QF = [(97, 89, 90, "9/7", "Boston", "United States"),
      (98, 93, 94, "10/7", "Los Ángeles", "United States"),
      (99, 91, 92, "11/7", "Miami", "United States"),
      (100, 95, 96, "11/7", "Kansas City", "United States")]
SF = [(101, 97, 98, "14/7", "Dallas", "United States"),
      (102, 99, 100, "15/7", "Atlanta", "United States")]
FINAL = (104, 101, 102, "19/7", "MetLife Stadium, NY/NJ", "United States")


def rank_key(team, table, fairplay):
    """Orden deterministico: pts, DG, GF, fair play (deduccion menos negativa), nombre."""
    pts, gf, gc = table[team]
    return (-pts, -(gf - gc), -gf, -fairplay.get(team, 0), team)


def standings(results, matches, fairplay):
    """results: {match_id: (hs, as)} para los 72 partidos.
    Devuelve {grupo: [equipos ordenados 1..4]} y la tabla cruda."""
    table = {t: [0, 0, 0] for g in GROUPS.values() for t in g}  # pts, gf, gc
    for m in matches:
        hs, as_ = results[m["match_id"]]
        h, a = m["home"], m["away"]
        table[h][1] += hs; table[h][2] += as_
        table[a][1] += as_; table[a][2] += hs
        if hs > as_:
            table[h][0] += 3
        elif hs < as_:
            table[a][0] += 3
        else:
            table[h][0] += 1; table[a][0] += 1
    ranked = {g: sorted(ts, key=lambda t: rank_key(t, table, fairplay))
              for g, ts in GROUPS.items()}
    return ranked, table


def best_thirds(ranked, table, fairplay):
    """Los 8 mejores terceros (reglamento: pts, DG, GF, fair play)."""
    thirds = [ranked[g][2] for g in GROUPS]
    thirds.sort(key=lambda t: rank_key(t, table, fairplay))
    return thirds[:8]


def assign_thirds(qualified_groups):
    """Asigna los 8 grupos de los terceros clasificados a las 8 llaves con
    cupo de tercero, respetando los cupos oficiales. Backtracking."""
    slots = [(n, set(allowed)) for n, (_, _), (kind, allowed), *_ in
             [(m[0], m[1], m[2], m[3]) for m in R32] if kind == "T"]
    # ordenar por menos opciones disponibles
    slots = [(n, allowed & set(qualified_groups)) for n, allowed in slots]
    slots.sort(key=lambda s: len(s[1]))
    assignment = {}

    def bt(i, used):
        if i == len(slots):
            return True
        n, options = slots[i]
        for g in sorted(options - used):
            assignment[n] = g
            if bt(i + 1, used | {g}):
                return True
            del assignment[n]
        return False

    if not bt(0, set()):
        # sin matching perfecto (raro): asignacion greedy permisiva
        used = set()
        for n, options in slots:
            pick = sorted(options - used) or sorted(set(qualified_groups) - used)
            assignment[n] = pick[0]
            used.add(pick[0])
    return assignment  # {nro_partido: grupo_del_tercero}


def build_r32(results, matches, fairplay):
    """Resuelve los 16 cruces de 16avos a partir de resultados completos de grupos."""
    ranked, table = standings(results, matches, fairplay)
    thirds = best_thirds(ranked, table, fairplay)
    third_by_group = {}
    for t in thirds:
        for g, ts in GROUPS.items():
            if t in ts:
                third_by_group[g] = t
    tslots = assign_thirds(sorted(third_by_group))

    fixtures = []
    for n, sh, sa, date, venue, country in R32:
        def resolve(slot):
            kind, val = slot
            if kind == "W":
                return ranked[val][0]
            if kind == "R":
                return ranked[val][1]
            return third_by_group[tslots[n]]
        fixtures.append({"n": n, "home": resolve(sh), "away": resolve(sa),
                         "date": date, "venue": venue, "country": country})
    return fixtures, ranked, table, thirds
