# Plan SimuMundial v2 — mejorar el modelo + sacar el ranking + rebrand

> **Para Codex**: ejecutar por fases, en orden, un commit por fase, verificando cada una antes de seguir (sección "Orden de ejecución"). Las decisiones ya están tomadas con Facu — no reabrirlas. Si algo del entorno bloquea (red, permisos, espacio), anotarlo en `PENDIENTES_WEBAPP.md` como siempre y seguir con lo que sí se pueda. Plan escrito por Claude el 12/6/2026 tras exploración del código; los números de línea son orientativos.

## Contexto

Hay **dos productos** que comparten el pipeline Python:

1. **Análisis personal** (`mundial2026.html`): predicción de la fase de grupos para uso de Facu. Se regenera solo con `update.py` — toda mejora del modelo le llega gratis. No requiere trabajo propio en este plan.
2. **El juego web** (`web/`): el jugador carga los 72 resultados de grupos y el modelo simula las eliminatorias hasta el campeón. **No es un prode**: no hay competencia de puntajes entre jugadores. Por eso se elimina la pantalla `/ranking` ("tabla de prode") y se renombra la marca de "Prode Mundial 2026" a **SimuMundial**.

El modelo actual es Elo propio (K 20–60, `build_profiles.py:28-40`) → Poisson con inflación de empates rho=1.10 (`predict.py:25`) → Monte Carlo 10k (`simulate.py:22`). Mejoras decididas: **solo APIs gratuitas** (football-data.org, The Odds API, eloratings.net) + mejoras matemáticas (Dixon-Coles, decay temporal, calibración con backtesting).

Decisiones ya tomadas por Facu:
- APIs: solo gratis. Sin API-Football pago.
- El contador "Reales acertados: X exactos · Y 1X2" de `/prode` **se queda** (es feedback informativo, no competencia).
- Rebrand: **SimuMundial** (como el repo).

---

## FASE 1 — Web: eliminar /ranking + rebrand SimuMundial

### 1.1 Eliminar /ranking (inventario exacto, verificado por exploración)

- **Borrar** `web/app/ranking/page.tsx`.
- `web/components/MundialGroups.tsx` (~líneas 335-336): sacar el `<Link href="/ranking">Ver ranking</Link>` de `final-actions`. **Ojo**: `.final-actions` usa `grid-template-columns: repeat(4, ...)` en `globals.css` (~línea 1067) → pasar a `repeat(3, ...)`.
- `web/app/sitemap.ts`: sacar `"/ranking"` del array.
- `web/lib/data.server.ts`: borrar `getStoredProdes()` (su único consumidor era el ranking). **Conservar** `getModelPicks()` (lo usa `/prode`).
- `scripts/update.py` → `copy_web_data()`: dejar de copiar `prode/*.json` a `web/data/prodes/`; borrar `web/data/prodes/` del repo. La carpeta raíz `prode/` y `scripts/game.py` (ranking local en `juego.html`) **quedan intactos**: son la herramienta personal de Facu.
- `web/app/globals.css`: borrar las reglas `.ranking-shell`, `.ranking-header`, `.ranking-table`, `.ranking-row*` (bloques ~581-627 y ~675-680) **y** sacar `.ranking-shell` de los selectores agrupados del pase visual (`.home-shell,.prode-shell,.ranking-shell,.world-shell`, `.prode-shell,.ranking-shell { padding }`, `.ranking-shell .visual-backdrop`, etc. — grepear `ranking` en el CSS).
- `web/e2e/prode-flow.spec.ts`: borrar el test `"/ranking muestra al modelo"` (líneas ~77-80). El resto de los 15 tests queda igual.
- **Conservar**: `web/lib/scoring.ts`, el contador en `ProdeBuilder` y el test de vitest `"scores facu like the current juego.html snapshot"` (valida paridad con Python; sigue vigente porque scoring se usa en `/prode`).

### 1.2 Rebrand "Prode Mundial 2026" → "SimuMundial"

Decisiones explícitas:
- **Las rutas NO cambian** (`/prode`, `/mundial` quedan): los links compartidos `?p=` y los tests dependen de ellas; renombrar rutas no aporta.
- **Las keys de localStorage NO cambian** (`prode-mundial-2026:draft`/`saved` en `web/lib/storage-keys.ts`): son internas y renombrarlas borraría drafts de usuarios.
- Cambia todo lo **visible**: 
  - `web/app/layout.tsx`: metadata title/template/description → "SimuMundial — Simulá tu Mundial 2026".
  - Metadata específica de `/`, `/prode`, `/mundial` (title/description/OG).
  - `web/app/manifest.ts`: name/short_name → SimuMundial.
  - `web/app/api/og/route.tsx`: textos "Prode Mundial 2026" → "SimuMundial" (kicker y título genérico). No tocar la lógica (satori: mantener PNG de fondo y `display:flex`; verificar con curl después).
  - Copys en componentes: "prode" en textos de UI → "carga"/"resultados"/"mundial" según contexto. Ejemplos: "Armar otro prode" → "Armar otro mundial", "Editar este prode" → "Editar resultados", "Importar prode JSON" → "Importar resultados JSON", "Mundial pronosticado de X" queda (ya es correcto). El import sigue aceptando los mismos `prode_*.json`.
  - `README.md` y `PENDIENTES_WEBAPP.md`: actualizar nombre.
- **Tests**: los e2e asertan textos ("Confirmar y revelar", "Importado: 72/72 partidos.", "Armá tu Mundial", "Reproducir desde el grupo A", "Saltear todo"). Si un copy asertado cambia, actualizar test y copy **en el mismo commit**. Recomendado: no tocar esos cinco textos.

### Verificación Fase 1
`npx tsc --project web/tsconfig.json --noEmit` · `npm run test` (9 verdes) · `npm run test:e2e` (15 verdes, ya sin el de ranking) · `npm run build` · curl `/api/og` (200 image/png) · `/ranking` debe dar 404.

---

## FASE 2 — Datos externos (fetchers nuevos, solo gratis)

### 2.0 Suscripciones (las hace Facu a mano, antes o en paralelo)

1. **football-data.org** → registrarse gratis en https://www.football-data.org/client/register → llega token por mail. Free tier alcanza para el Mundial. `fetch_fixture.py` **ya lo soporta** vía env `FOOTBALL_DATA_KEY` (línea 184): con token usa la API oficial y Wikipedia queda de fallback.
2. **The Odds API** → registrarse gratis en https://the-odds-api.com → API key, 500 requests/mes. Una request devuelve TODOS los partidos del Mundial con cuotas (sport key `soccer_fifa_world_cup`), así que 1 corrida diaria ≈ 30 req/mes: sobra.
3. **eloratings.net** → no requiere registro: sirve sus datos como TSV plano (ej. `https://www.eloratings.net/World.tsv`, el mismo que consume su frontend). Se scrapea.

### 2.1 Manejo de secretos: `.env` en la raíz

**Estado al 12/6 (ya hecho por Claude — Codex NO debe rehacerlo):**
- `B:\mundial\.env` YA EXISTE con `FOOTBALL_DATA_KEY` y `ODDS_API_KEY` cargados (gitignoreado). `.env.example` y la entrada en `.gitignore` ya están commiteados.
- `FOOTBALL_DATA_KEY` **verificada**: `GET https://api.football-data.org/v4/competitions/WC` con header `X-Auth-Token` → 200 OK.
- `ODDS_API_KEY` devolvió **401** en `GET https://api.the-odds-api.com/v4/sports/?apiKey=...` → probablemente falta confirmar el mail de registro de the-odds-api.com (Facu: revisá el mail de confirmación). Re-testear con:
  `curl "https://api.the-odds-api.com/v4/sports/?apiKey=$ODDS_API_KEY"` (ese endpoint no gasta cuota). Si sigue 401, regenerar la key en el dashboard.

**Lo que SÍ falta hacer (Codex):**
- En `scripts/update.py`, un parser de ~10 líneas que lea `.env` si existe y haga `os.environ.setdefault(k, v)` antes de correr los pasos (sin dependencias nuevas).
- Documentar en README.

### 2.2 `scripts/fetch_elo.py` (nuevo) → `data/elo_world.json`

- Descargar `https://www.eloratings.net/World.tsv` (User-Agent de navegador; el formato es TSV con columnas posicionales: revisar el formato real al implementar — el frontend de eloratings lo parsea por índice; rank/equipo/rating están en columnas fijas).
- Mapear nombres al inglés de martj42 usando `ALIASES`/equipos de `scripts/teams.py` (eloratings usa códigos/nombres propios, ej. "USA", "South Korea": extender ALIASES donde haga falta). Loggear equipos del fixture que no matchearon.
- Salida: `{"updated": iso, "elo": {"Argentina": 2150, ...}}` solo para los 48 clasificados (con los demás no hacemos nada).
- **Best-effort como `fetch_rankings.py`**: si falla red o cambia el formato, warning y el pipeline sigue (el blend usa solo Elo propio).
- Cache: si el archivo tiene <12h, no re-descargar (mismo patrón que history 3 días).

### 2.3 `scripts/fetch_odds.py` (nuevo) → `data/odds.json`

- `GET https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds/?apiKey=...&regions=eu&markets=h2h` (una sola request por corrida).
- Por partido: promediar cuotas h2h de los bookmakers, **quitar el margen** (overround): `p_i = (1/odds_i) / Σ(1/odds_j)` → guardar `{match_id: {p1, px, p2, bookmakers: n}}` mapeando equipos al `match_id` del fixture (por nombres + fecha; los nombres de la API vienen en inglés, usar ALIASES).
- Best-effort + cache 12h. Si no hay `ODDS_API_KEY` o falla: warning y seguir sin odds.
- Registrar en el JSON el header `x-requests-remaining` que devuelve la API para monitorear la cuota.

### 2.4 Integrar al pipeline

En `update.py`, agregar pasos entre el 3 y el 4: `3b/ Elo externo (fetch_elo)` y `3c/ Cuotas (fetch_odds)`. Ambos opcionales/best-effort. **Importante para el sandbox de Codex**: no asumir red — los fetchers deben tener `--offline`/detección de falta de red y los tests usar fixtures locales (JSON de ejemplo en `tests/fixtures/`).

---

## FASE 3 — Modelo v2

### 3.1 Ratings (`build_profiles.py`)

- **Blend de Elo**: `elo = 0.5 * elo_propio + 0.5 * elo_externo` cuando `data/elo_world.json` tiene al equipo; si no, `elo_propio`. Guardar los tres en `team_profiles.json`: `elo` (el blend, lo que consume todo lo demás), `elo_own`, `elo_external`. El peso 0.5 es constante nombrada `ELO_BLEND_W` — el backtest (3.4) puede ajustarlo.
- **Decay temporal en la forma**: `avg_gf_2y`/`avg_gc_2y` pasan a promedio ponderado exponencial con half-life de 18 meses (peso `0.5 ** (días/548)`), manteniendo los mismos nombres de campo (la web los consume tal cual: paridad sin tocar TS).
- **Shrinkage**: si `matches_2y < 10`, tirar los promedios hacia la media global de los 48 clasificados: `avg = (n*avg + (10-n)*media_global) / 10`.

### 3.2 Predicción de grupos (`predict.py`)

- **Dixon-Coles real**: reemplazar la inflación diagonal `rho=1.10` por la corrección τ(i,j) de Dixon-Coles que ajusta SOLO los scores bajos (0-0, 1-0, 0-1, 1-1) con parámetro `RHO_DC` (arrancar en `-0.10`, lo calibra el backtest). La matriz se renormaliza igual. Mantener `MAX_G=8`, `MIN_LAMBDA=0.18`.
- **Blend con mercado**: si `data/odds.json` tiene el partido → `p_blend = W_ODDS * p_mercado + (1 - W_ODDS) * p_modelo` con `W_ODDS = 0.6` (constante nombrada). Para que `score_pred` y lambdas sean coherentes con `p_blend`: ajustar el `diff` de Elo efectivo invirtiendo `elo_we` para reproducir `p1_blend/(p1_blend+p2_blend)` y recalcular lambdas con ese diff (el total esperado no cambia). Guardar en predictions.json: `p1/px/p2` (los del blend), `p1_model/px_model/p2_model` y `p1_market/...` cuando existan, para poder comparar.
- predictions.json mantiene el mismo shape para los campos que la web consume (`score_pred`, `p1/px/p2`): **la web no necesita cambios**.

### 3.3 Paridad TypeScript (regla estricta)

- La web simula eliminatorias con `web/lib/model.ts` (koMatrix) alimentado por `team_profiles.json`. **Decisión**: el motor TS NO se toca en este plan — las mejoras le llegan vía datos (Elo blend + forma con decay en team_profiles). Así `decode(encode)` y el sorteo determinístico no cambian de semántica y los 15 e2e siguen verdes.
- **Excepción**: si en Python se cambia `ko_matrix` de `game.py` (no está en este plan), hay que portar lo mismo a `model.ts` y actualizar los tests de paridad de `web/tests/sprint1.test.ts`. Evitarlo en esta pasada.
- Si el backtest cambia constantes compartidas (`HOME_ADV`, `BASE_TOTAL`): actualizarlas en `predict.py` **y** `web/lib/model.ts` en el mismo commit, y correr vitest + e2e.

### 3.4 Backtesting (`scripts/backtest.py` — nuevo)

- Para cada Mundial 2014/2018/2022: congelar `history.csv` al día anterior al partido inaugural, recalcular Elo y perfiles con ese corte, predecir los 48/64 partidos del torneo (martj42 los tiene con `tournament = "FIFA World Cup"`), y medir contra los resultados reales:
  - **Log-loss** y **Brier score** multinomial del 1X2 (métrica principal).
  - **RPS** (ranked probability score).
  - % de aciertos de resultado exacto del `score_pred`.
  - Baseline de control: predicción uniforme (1/3) y predicción "siempre gana el de mayor Elo".
- **Grid-search** sobre: `K-factors` (escala ±50%), `HOME_ADV` (0–120, ojo: en mundiales casi todo es neutral, solo cuenta para anfitriones), `RHO_DC` (-0.20..0), `BASE_TOTAL` (2.3–2.9), peso del decay (half-life 12/18/24 meses). `ELO_BLEND_W` y `W_ODDS` no se pueden backtestear sin datos históricos de eloratings/odds → quedan en 0.5/0.6 documentados como decisión a priori, configurables por env.
- Salida: `data/backtest_report.json` + tabla legible en consola. **Los parámetros ganadores se fijan como constantes en el código con un comentario que cite el resultado del backtest** (ej. `RHO_DC = -0.08  # backtest 2014-2022: logloss 0.98 vs 1.02 del rho viejo`).
- Si Dixon-Coles + parámetros nuevos NO mejoran el log-loss del modelo actual en el backtest, **no se adoptan** (criterio objetivo, sin vueltas).

### 3.5 Reglas de integridad (no negociables)

- `data/model_picks.json` está **congelado**: `game.py:148` ya garantiza que un pick existente nunca se pisa. El modelo nuevo solo genera picks para partidos futuros sin pick previo. No regenerar el archivo.
- Los prodes guardados en `prode/*.json` no se tocan.
- El sorteo determinístico por semilla (md5 nombre+resultados) no cambia.

---

## Orden de ejecución para Codex (cada fase = commit propio, verificada antes de seguir)

1. **Fase 1** (web): ranking fuera + rebrand. Verificación: tsc, vitest 9, e2e 15, build, curl OG.
2. **Fase 2** (fetchers + .env): con fixtures offline para tests; Facu corre los fetches reales con sus tokens.
3. **Fase 3.4 primero** (backtest del modelo ACTUAL como baseline) → después 3.1/3.2 con el backtest como juez → fijar constantes ganadoras.
4. Re-correr `python scripts/update.py` completo (lo corre Facu, el sandbox no tiene red/permisos), revisar predictions a ojo, `copy_web_data`, suite web completa.
5. Actualizar `PENDIENTES_WEBAPP.md` y `README.md` con lo hecho y lo que quede.

## Verificación final end-to-end

- `python scripts/backtest.py` → reporte con mejora de log-loss documentada vs baseline.
- `python scripts/update.py` → pipeline completo sin errores, con y sin tokens en `.env`.
- Web: `npm run test` + `npm run test:e2e` + `npm run build` verdes; `/ranking` 404; marca SimuMundial en título, OG y manifest; "Completar con modelo" usa las predicciones nuevas.
- `juego.html` (Python) sigue generándose con su ranking local intacto.
