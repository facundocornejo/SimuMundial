# SimuMundial

Web app Next.js en `web/` más pipeline Python local como proveedor de datos.

## Flujo diario

```bash
python scripts/update.py
git add -A
git commit -m "datos"
git push
```

`scripts/update.py` actualiza los JSON del pipeline y copia:

- `data/fixture.json`
- `data/team_profiles.json`
- `data/predictions.json`
- `data/model_picks.json`

a `web/data/` para el deploy.

El pipeline lee `.env` desde la raiz si existe y carga sus variables con
`os.environ.setdefault`, sin pisar variables ya exportadas por la terminal.
Variables soportadas:

- `FOOTBALL_DATA_KEY`: opcional, mejora `fetch_fixture.py`.
- `ODDS_API_KEY`: opcional, habilita `scripts/fetch_odds.py`.

Fetchers externos agregados:

- `scripts/fetch_elo.py` genera `data/elo_world.json` desde eloratings.net.
- `scripts/fetch_odds.py` genera `data/odds.json` desde The Odds API.
- Ambos tienen cache de 12h y modo offline/fixture para pruebas locales.

## Web

Desde la raiz del repo:

```bash
npm install
npm run dev
npm run test
npm run build
```

Tambien se puede trabajar entrando directo a `web/`:

```bash
cd web
npm install
npm run dev
npm run test
npm run build
```

Rutas principales:

- `/` landing y mundiales guardados localmente
- `/prode` carga de resultados carta por carta o planilla
- `/mundial?p=<codigo>` revelación de grupos y cuadro
