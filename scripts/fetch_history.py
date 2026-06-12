# -*- coding: utf-8 -*-
"""Baja el historico de partidos internacionales (martj42, 1872-presente).

Salida: data/history.csv  (cache de 3 dias; --force para re-bajar)
"""
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
CACHE_DAYS = 3


def main(force=False):
    DATA.mkdir(exist_ok=True)
    dest = DATA / "history.csv"
    if dest.exists() and not force:
        age_days = (time.time() - dest.stat().st_mtime) / 86400
        if age_days < CACHE_DAYS:
            print(f"history.csv en cache ({age_days:.1f} dias, < {CACHE_DAYS}); uso local. --force para re-bajar")
            return 0
    print("Bajando historico martj42 (~5 MB)...")
    r = requests.get(URL, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    lines = r.text.count("\n")
    print(f"OK history.csv: ~{lines} partidos")
    return 0


if __name__ == "__main__":
    sys.exit(main(force="--force" in sys.argv))
