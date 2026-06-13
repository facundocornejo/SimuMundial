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

## Modelo de predicción

Arquitectura: Elo → Poisson con inflación de empate (Dixon-Coles simplificado) →
Monte Carlo. Las constantes están calibradas por backtest con validación train/test
(`scripts/backtest.py`, modo sweep). Las predicciones 1X2 mostradas de los partidos
con cuota disponible se mezclan hacia el mercado (`MARKET_BLEND_W` en `predict.py`,
60% modelo / 40% mercado), porque las casas de apuestas son el predictor mejor
calibrado. `data/model_picks.json` (autocompletar prode) se mantiene como modelo puro.

**Sincronización Python ↔ TypeScript:** si cambian las constantes del modelo en
`scripts/predict.py` / `scripts/build_profiles.py`, hay que reflejarlas en
`web/lib/model.ts` (`HOME_ADV`, `RHO`, `BASE_TOTAL`, `TOTAL_BLEND_W`).

## Deploy a Vercel

La web es el subdirectorio `web/` (monorepo con el pipeline Python en la raíz).

Configuración inicial (una sola vez, en el dashboard de Vercel):

1. Importar el repo `facundocornejo/SimuMundial`.
2. **Root Directory = `web`** (clave: la app vive ahí, no en la raíz).
3. Framework: Next.js (autodetectado). Build/Output por defecto.
4. **No hace falta configurar variables de entorno**: el runtime solo lee JSON
   precomputado de `web/data/`; los tokens de API son solo para el pipeline local.

Después de eso, cada `git push` a `main` dispara un redeploy automático. El flujo de
actualización de datos es el de "Flujo diario": `python scripts/update.py` (regenera y
copia a `web/data/`) + commit + push.
