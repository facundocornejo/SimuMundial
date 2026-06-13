# Pendientes web app SimuMundial

## PLAN_V2 - Fase 1 cerrada: rebrand SimuMundial y sin `/ranking`

Hecho en esta fase:

- Se elimino la ruta web `/ranking`; ahora responde 404.
- Se saco el link `Ver ranking` de las acciones finales de `/mundial`.
- Las acciones finales quedaron en 3 opciones:
  - `Reproducir desde el grupo A`
  - `Editar resultados`
  - `Armar otro mundial`
- Se elimino `/ranking` del sitemap.
- Se borro `getStoredProdes()` de `web/lib/data.server.ts`; `getModelPicks()` queda intacto.
- `scripts/update.py` ya no copia `prode/*.json` a `web/data/prodes`.
- Se removieron los archivos trackeados de `web/data/prodes/`.
- Se elimino el e2e especifico de `/ranking`.
- Se saco CSS especifico de ranking y referencias `.ranking-*` del pase visual.
- Rebrand visible de la web a `SimuMundial` en metadata, manifest, OG, home y pantallas base.
- Se conservaron rutas `/prode` y `/mundial`, keys de localStorage, codec/import/export y textos e2e protegidos.

Verificado en esta fase:

- `npx tsc --project web/tsconfig.json --noEmit --incremental false`: OK.
- `npm run test`: OK, 9 tests verdes.
- `npm run test:e2e` partido por proyectos por limite del canal:
  - `desktop`: OK, 7 tests verdes.
  - `mobile-390`: OK, 7 tests verdes.
- `/ranking`: 404.
- `/api/og`: 200 `image/png`.
- Home renderiza marca visible `SimuMundial`.

Bloqueos de entorno en esta fase:

- El comando exacto `npx tsc --project web/tsconfig.json --noEmit` intenta escribir `web/tsconfig.tsbuildinfo` y falla con `EPERM`; por eso la verificacion de source se corrio con `--incremental false`.
- `npm run build` sigue bloqueado por `EPERM` al abrir `web/.next/trace`, igual que en corridas anteriores desde Codex.
- La limpieza completa de `web/.next` tambien fue bloqueada por Windows (`EPERM` sobre archivos generados). Se borro solamente el stale `web/.next/types/validator.ts` que todavia referenciaba `/ranking`; Next lo regenera.
- `git add`/`git commit` desde Codex quedaron bloqueados: el sandbox tiene `.git` en solo lectura (`Permission denied` al crear `.git/index.lock`) y el intento elevado por PowerShell falla antes de ejecutar git por el error CET de Windows.

## PLAN_V2 - Fase 2 cerrada: fetchers externos gratuitos + parser `.env`

Hecho en esta fase:

- `scripts/update.py` ahora lee `.env` desde la raiz y carga variables con `os.environ.setdefault`, sin pisar variables ya exportadas.
- Se agrego `scripts/fetch_elo.py`:
  - descarga `https://www.eloratings.net/World.tsv`;
  - normaliza nombres contra `teams.py`;
  - genera `data/elo_world.json`;
  - cachea 12h;
  - soporta `--fixture`, `--offline`, `--force` y `--output`.
- Se agrego `scripts/fetch_odds.py`:
  - usa The Odds API con `ODDS_API_KEY`;
  - calcula probabilidades 1X2 sin margen;
  - mapea por equipos + fecha al `match_id`;
  - genera `data/odds.json`;
  - cachea 12h;
  - soporta `--fixture`, `--offline`, `--force` y `--output`.
- `scripts/update.py` integra ambos pasos como `3b/9 Elo externo` y `3c/9 Cuotas`, despues del ranking FIFA y antes de `build_profiles.py`.
- Se agregaron fixtures offline:
  - `tests/fixtures/elo_world.tsv`
  - `tests/fixtures/odds_worldcup.json`
- `README.md` documenta `.env`, `FOOTBALL_DATA_KEY`, `ODDS_API_KEY` y los nuevos fetchers.
- No se tocaron `.env`, `.env.example`, `data/model_picks.json` ni `prode/*.json`.
- Correccion posterior: `eloratings.net/World.tsv` real trae codigo de seleccion, no nombre. `scripts/fetch_elo.py` ahora mapea esos codigos y valida `48/48` equipos contra la fuente real.
- Correccion posterior: `scripts/fetch_odds.py` y `scripts/fetch_elo.py` ahora leen `.env` cuando se ejecutan directo; los caches vacios ya no se consideran validos.

Verificado en esta fase:

- `python scripts/fetch_elo.py --fixture tests/fixtures/elo_world.tsv --output <temp> --force`: OK, parsea 10/48 equipos de fixture.
- `python -B scripts/fetch_elo.py --output <temp> --force`: OK contra `World.tsv` real, `48/48` equipos.
- `python scripts/fetch_odds.py --fixture tests/fixtures/odds_worldcup.json --output <temp> --force`: OK, mapea 2 partidos a `match_id`.
- Facu corrio `python scripts/fetch_elo.py --force`: OK, `48/48` equipos.
- Facu corrio `python scripts/fetch_odds.py --force`: OK, `69` partidos con mercado.
- Facu corrio `python scripts/update.py --force`: OK, pipeline completo; fixture 72 partidos, 3 jugados, validacion final OK, datos copiados a `web/data`.
- Parser `.env` probado con archivo temporal: respeta `setdefault` y no pisa variables existentes.
- Carga de scripts Python con `python -B`: OK.
- `npx tsc --project web/tsconfig.json --noEmit --incremental false`: OK.
- `npm run test`: OK, 9 tests verdes.
- `npm run test:e2e` partido por proyectos:
  - `desktop`: OK, 7 tests verdes.
  - `mobile-390`: OK, 7 tests verdes.

Bloqueos de entorno en esta fase:

- `python -m py_compile` no puede escribir en `scripts/__pycache__` por `Permission denied`; se verifico con `python -B` sin generar `.pyc`.
- `npm run build` sigue bloqueado por `EPERM` en `web/.next/trace`.
- Commit de fase sigue pendiente por bloqueo de `.git`/CET detallado arriba.

## PLAN_V2 - Fase 3 cerrada: backtest y decision de modelo

Hecho en esta fase:

- Se agrego `scripts/backtest.py`.
- El backtest hace replay rolling del historial:
  - predice antes de actualizar Elo con el resultado observado;
  - usa log-loss 1X2 como metrica principal;
  - compara `baseline` contra `v2_candidate`;
  - soporta `--output` para correr en temporal cuando Python no puede escribir en `data/`.
- Se genero `data/backtest_report.json` con el resultado del baseline y la decision.
- Se probo una calibracion acotada del candidato v2.
- Nota: `data/elo_world.json` y `data/odds.json` ya se generan bien, pero el modelo final actual no los incorpora porque la adopcion v2 quedo rechazada por backtest.
- Por criterio del plan, no se adopto el modelo v2 porque no supero el baseline:
  - baseline log-loss: `0.887032`
  - v2 candidate log-loss: `0.889519`
  - delta: `+0.002487` (peor; menor es mejor)
- No se tocaron `build_profiles.py`, `predict.py` ni `web/lib/model.ts` como modelo final.
- `data/model_picks.json` no tiene diff contra Git.

Verificado en esta fase:

- `python -B scripts/backtest.py --output <temp>`: OK.
- `python -B scripts/backtest.py`: calcula pero falla al escribir `data/backtest_report.json` por permisos del entorno; el reporte quedo agregado con `apply_patch`.
- `npx tsc --project web/tsconfig.json --noEmit --incremental false`: OK.
- `npm run test`: OK, 9 tests verdes.
- `npm run test:e2e` partido por proyectos:
  - `desktop`: OK, 7 tests verdes.
  - `mobile-390`: OK, 7 tests verdes.

Bloqueos de entorno en esta fase:

- `python scripts/backtest.py` sin `--output` no puede sobrescribir `data/backtest_report.json` por `Permission denied` desde Python.
- `python scripts/update.py` real queda pendiente para Facu: en Codex hay bloqueo de escritura Python sobre `data/` y las corridas reales contra APIs deben hacerse desde la terminal local con tokens/red.
- Despues de la correccion de Elo, falta rerun local de `python scripts/update.py` para regenerar `data/elo_world.json` real con `48/48`.
- `npm run build` sigue bloqueado por `EPERM` en `web/.next/trace`.
- Commit de fase sigue pendiente por bloqueo de `.git`/CET detallado arriba.

Estado actual: los 5 sprints del plan base quedaron implementados en codigo. Tambien quedaron aplicadas las correcciones de reinicio/coherencia, validacion fuerte, SEO/seguridad y la pasada visual premium con assets PNG generados.

## Actualizacion: visual premium broadcast

Hecho en esta pasada:

- Se aplico una direccion visual `broadcast premium mundialista`, original y sin marca FIFA.
- Se agregaron assets locales en `web/public/media/`. Hay dos familias:
  - SVG livianos de fallback, creados desde Codex.
  - PNG cinematicos generados, movidos manualmente desde `C:\Users\facu\.codex\generated_images\019eba33-8d2d-7423-bdbc-662fd93137f4\`.
- PNG activos en codigo:
  - `hero-stadium.png`
  - `prode-boardroom.png`
  - `world-tunnel.png`
  - `phase-groups.png`
  - `phase-knockout.png`
  - `trophy-generic.png`
  - `og-default.png`
- SVG fallback disponibles:
  - `hero-stadium.svg`
  - `prode-boardroom.svg`
  - `world-tunnel.svg`
  - `phase-groups.svg`
  - `phase-knockout.svg`
  - `trophy-generic.svg`
  - `og-default.svg`
- Se actualizo `web/components/VisualBackdrop.tsx` para que la app use los PNG reales.
- Se actualizo `/api/og` para usar `og-default.png`.
- Se agrego `web/components/VisualBackdrop.tsx` con:
  - `VisualBackdrop`
  - `HeroMedia`
  - `PhaseAtmosphere`
  - `TrophyVisual`
- `/` ahora tiene hero full-bleed con atmosfera de estadio, copy encima y panel local tipo sidebar de transmision.
- `/prode` mantiene la carga eficiente, pero suma fondo tactico y superficies mas sobrias.
- `/mundial` ahora tiene fondos por fase, barrido de luz, motion liviano y visual propio de copa en la final.
- `/ranking` se ajusto hacia scoreboard premium.
- `/api/og` usa el fondo social nuevo y elimina el emoji de copa del render OG.
- Se cambio el sistema visual:
  - tinta/nocturno
  - verdes cancha
  - ambar de reflectores
  - blanco tiza
  - rojo senal puntual
- Se reemplazo el look cyan/purpura generico por tokens mas deportivos.
- Se agregaron animaciones CSS livianas con `transform` y `opacity`, respetando `prefers-reduced-motion`.
- Se actualizaron metadata/manifest para el nuevo color de marca e imagen OG dinamica.

Verificado en esta pasada:

- `npm run test`: OK, 9 tests verdes.
- `tsc --project web/tsconfig.json --noEmit --incremental false`: OK, sin errores.
- `npm run build`: bloqueado por permisos del entorno al escribir `web/.next/trace`.

Conversion WebP (hecha el 2026-06-12 por Claude):

- Los 7 PNG se convirtieron a WebP con Pillow (quality 82): de 13.3MB totales a ~660KB.
- `VisualBackdrop.tsx` apunta a `.webp` en todas las variantes.
- `/api/og` se queda con `og-default.png`: satori (next/og) NO soporta WebP como `<img>` (devuelve conexion vacia). No importa: ese fondo es server-side y no afecta el peso que baja el cliente.
- Se borraron los 6 PNG sin uso de `web/public/media/` (los originales siguen en `C:\Users\facu\.codex\generated_images\019eba33-8d2d-7423-bdbc-662fd93137f4\`).
- Los SVG livianos quedan como referencia/fallback.
- Verificado: 9 tests vitest, tsc limpio, 16 tests Playwright e2e verdes (desktop + mobile 390px).

Pendiente visual futuro:

- Three.js real queda para fase 2, solo si la version actual ya esta estable en mobile.
- Video loops quedan para fase 2; por ahora motion web liviano evita peso y problemas de autoplay.

Que sigue recomendado:

1. ~~Prueba visual manual en Chrome~~ — hecha por Facu el 2026-06-12.
2. ~~Correr `npm run build`~~ — hecho el 2026-06-12: build limpio desde cero (se borro `.next` antes), 10 rutas OK. Ademas se corrio `npm run start` y los 16 e2e de Playwright pasaron contra el server de produccion (la validacion mas cercana a Vercel posible).
3. Deploy a Vercel cuando Facu lo decida: la app ya esta lista tecnicamente (build limpio, e2e contra produccion, datos en `web/data/`, todo commiteado y pusheado).

## Actualizacion 2026-06-12 (Claude, fuera del sandbox de Codex)

Nota: esta verificacion fue anterior a la pasada visual premium con PNG activos. Despues de esa pasada hay que repetir `npm run build` desde tu terminal/admin.

Se destrabaron todos los pendientes por bloqueo de entorno, salvo el deploy:

- `npm install` desde la raiz: OK, workspace `web` instalado con `node_modules` y `package-lock.json` en la raiz.
- `python update.copy_web_data()`: OK, `web/data/` quedo con `fixture.json`, `team_profiles.json`, `predictions.json`, `model_picks.json` y `prodes/prode_facu.json`.
- `npm run test`: OK, 9 tests verdes.
- `npm run build`: OK, compila limpio y genera las 10 rutas. Queda un warning de Turbopack por lecturas dinamicas de filesystem en `lib/data.server.ts` (no bloquea).
- Dev server + smoke test HTTP: `/`, `/prode`, `/ranking` responden 200; `/mundial` sin `?p=` redirige 307 a `/prode`; `/mundial?p=<codigo invalido>` tambien redirige a `/prode`.
- **Bug encontrado y arreglado**: `/api/og` devolvia 500 en runtime (el build no lo detectaba). Causa: satori/next-og exige `display: flex` explicito en divs con mas de un hijo, y `🏆 {champion}` eran dos nodos JSX. Fix: template literal en `web/app/api/og/route.tsx`. Verificado: `/api/og` y `/api/og?p=<codigo de facu>` devuelven PNG 200 con campeon Argentina.
- Se valido el flujo `?p=` con el codigo real del prode de facu (199 caracteres): `/mundial?p=` responde 200.

Sigue pendiente:

- Prueba visual/manual completa en navegador (autoplay, responsive 390px, editar prode, borrar guardados, etc.).
- Repetir `npm run build` despues de los cambios visuales y assets PNG.
- Deploy a Vercel (punto 5 de abajo).
- Las mejoras propuestas por Codex (seccion final), que son opcionales pre-deploy.

## Actualizacion: reinicio y coherencia de resultados

Hecho en esta pasada:

- Se separaron las fuentes visibles de resultado:
  - `pronostico`: lo que carga el jugador.
  - `real`: `fixture.score` solo si el partido esta `played`.
  - `modelo`: `predictions.score_pred` / `model_picks` cuando se usa para completar.
- `/prode` ahora muestra labels claros:
  - `Tu pronostico`
  - `Resultado real`
  - `Modelo`
  - `Completado por modelo`
- `/mundial` ahora habla de `Mundial pronosticado`, `Tu Grupo A`, `Tabla segun tu pronostico` y resultados reales como referencia secundaria.
- En grupos de `/mundial`, cada partido muestra el pronostico principal y, si existe, una linea secundaria con el resultado real.
- En eliminatorias se aclara que el cuadro se sortea desde el bracket pronosticado.
- Se agregaron acciones finales en `/mundial`:
  - `Reproducir desde el grupo A`
  - `Ver ranking`
  - `Editar este prode`
  - `Armar otro prode`
- `/prode?new=1` fuerza carga limpia e ignora el draft viejo.
- `Editar este prode` abre `/prode?p=<codigo>` y carga ese codigo como draft editable.
- Al confirmar un prode se borra el draft actual para que no reaparezca la primera sesion.
- `worldRevealState` ya no se usa como persistencia del reveal y se limpia en acciones de carga nueva.
- Se agrego boton `Borrar prodes guardados` en la landing.
- Se centralizaron keys de storage:
  - `prode-mundial-2026:draft`
  - `prode-mundial-2026:saved`
- Se agregaron helpers compartidos:
  - `isValidScore(score)`
  - `validateProde(prode, matchIds)`
  - `normalizeImportedProde(json, matchIds)`
- Import JSON ahora descarta campos extra y reporta:
  - partidos importados
  - partidos faltantes
  - ids desconocidos
  - scores invalidos
- `/mundial?p=` redirige a `/prode` si el codigo es invalido, incompleto o tiene scores invalidos.
- `/api/og` ahora tolera codigos invalidos y devuelve una tarjeta generica en vez de romper.
- Se agregaron headers de seguridad en `web/next.config.ts`.
- Se agregaron `robots.ts`, `sitemap.ts`, `manifest.ts` y `not-found.tsx`.
- Se agrego metadata especifica para `/`, `/prode`, `/mundial` y `/ranking`.
- Se limpio CSS viejo no usado de la version anterior de `/mundial`.
- Se ampliaron tests de 4 a 9 casos.

Verificado en esta pasada:

- `npm run test`: OK, 9 tests verdes.
- `tsc --project web/tsconfig.json --noEmit --incremental false`: OK, sin errores.

No verificado por bloqueo del entorno Codex:

- `npm run build` sigue fallando antes de compilar por permisos al escribir `web/.next/trace-build`:

```text
EPERM: operation not permitted, open 'B:\mundial\web\.next\trace-build'
```

Conviene repetir `npm run build` desde tu terminal/admin, que ya pudo ejecutar la app.
Tambien intente pedir ejecucion fuera del sandbox, pero el runner de Windows fallo antes de correr npm con el error de CET del entorno.

Pendiente tecnico despues de esta pasada:

- Partir `MundialGroups.tsx` en componentes mas chicos cuando el comportamiento quede confirmado manualmente.
- Hacer prueba visual/manual completa en navegador:
  - cargar Facu
  - confirmar
  - llegar a final
  - reproducir desde Grupo A
  - editar el prode existente
  - armar otro prode y confirmar draft limpio
  - borrar guardados desde landing

## Hecho

- `web/` creado con Next.js App Router, TypeScript y Tailwind/PostCSS.
- Motor TypeScript puro en `web/lib/`:
  - grupos y nombres de selecciones
  - posiciones y mejores terceros
  - bracket FIFA R32 a final
  - modelo Elo/Poisson
  - sorteo eliminatorio deterministico por semilla del prode
  - scoring del prode
  - codec compacto para `?p=`
- `/` landing con lista de prodes guardados en `localStorage`.
- `/prode` con:
  - carga carta por carta
  - modo planilla
  - autosave en `localStorage`
  - import de `prode_*.json`
  - completar faltantes con modelo
  - confirmacion y navegacion a `/mundial?p=<codigo>`
- `/mundial` con:
  - decodificacion de `?p=`
  - redireccion a `/prode` si falta o es invalido
  - revelacion de grupos
  - tablas y mejores terceros
  - controles visibles: autoplay, siguiente, saltear fase, saltear todo
  - respeto de `prefers-reduced-motion`
  - eliminatorias sorteadas de forma reproducible
  - cuadro responsive y campeon con confetti
- `/ranking` con jugadores de `prode/*.json` mas `🤖 Modelo`.
- `/api/og` con imagen OG basica.
- `generateMetadata` en `/mundial`.
- `scripts/update.py` actualizado con paso `10/10 Datos web app` para copiar datos a `web/data/`.
- `README.md` con flujo diario y comandos principales.

## Verificado

Verificaciones que pasaron en este entorno:

- `vitest run`: 4 tests verdes.
- Paridad contra Python:
  - posiciones de grupos
  - cruces de R32
  - puntaje de `facu`: exactos `1`, 1X2 `0`, puntos `3`
- `decode(encode(prode)) === prode`.
- Sorteo eliminatorio deterministico para el mismo prode.
- Chequeo sintactico TSX con `esbuild` para:
  - `/`
  - `/prode`
  - `/mundial`
  - `/ranking`
  - `/api/og`
  - `layout`

## Falta por bloqueo del entorno

Estas tareas no fallaron por logica de codigo, sino porque los procesos externos no pudieron escribir en `B:\mundial` o porque no habia espacio suficiente en Temp.

### 1. Instalar dependencias reales en `web/`

No se pudo ejecutar correctamente:

```bash
cd web
npm install
```

Motivo observado:

- `EPERM` al intentar crear `B:\mundial\web\package-lock.json`.
- Git Bash y Python tambien fallaron al escribir archivos dentro de `B:\mundial\web`.

Resultado pendiente:

- crear `web/package-lock.json`
- crear `web/node_modules/`
- dejar dependencias instaladas localmente

### 2. Correr build real de Next

No se pudo ejecutar:

```bash
cd web
npm run build
```

Motivos:

- sin `npm install`, no hay `node_modules`
- al intentar validar en una copia temporal, la instalacion fallo por `ENOSPC` en `C:\Users\facu\AppData\Local\Temp`

Resultado pendiente:

- confirmar que `next build` pasa limpio
- detectar errores especificos de Next/Vercel que `esbuild` no puede ver

### 3. Correr dev server y prueba visual/manual

No se pudo dejar corriendo:

```bash
cd web
npm run dev
```

Resultado pendiente:

- abrir `/`
- probar `/prode` manualmente
- recargar a mitad de carga y confirmar autosave
- importar `prode/prode_facu.json` y confirmar `72/72`
- confirmar navegacion a `/mundial?p=<codigo>`
- probar autoplay, siguiente, saltear fase y saltear todo
- revisar responsive en 390px y desktop
- revisar que el cuadro se vea bien y no haya solapamientos

### 4. Copiar fisicamente datos a `web/data/`

Se agrego la funcion en `scripts/update.py`, pero no se pudo ejecutar en este entorno:

```bash
python -c "import sys; sys.path.insert(0, r'B:/mundial/scripts'); import update; update.copy_web_data()"
```

Motivo observado:

```text
PermissionError: [Errno 13] Permission denied: 'B:\\mundial\\web\\data\\fixture.json'
```

Resultado pendiente:

- copiar `data/fixture.json` a `web/data/fixture.json`
- copiar `data/team_profiles.json` a `web/data/team_profiles.json`
- copiar `data/predictions.json` a `web/data/predictions.json`
- copiar `data/model_picks.json` a `web/data/model_picks.json`
- copiar `prode/*.json` a `web/data/prodes/`

Nota: el codigo de `web/lib/data.server.ts` puede leer desde `web/data/` para deploy y desde `../data`/`../prode` en local, asi que la app local puede funcionar antes de copiar, pero Vercel necesita `web/data/`.

### 5. Deploy Vercel

No se hizo deploy.

Resultado pendiente:

- crear/conectar repo remoto si hace falta
- configurar Vercel con `web/` como root directory
- correr build limpio antes de deploy
- probar URL desde celular
- probar preview OG con un link real `?p=`

## Comandos recomendados al reabrir con permisos de administrador

Desde `B:\mundial`:

```bash
python scripts/update.py
npm install
npm run test
npm run build
npm run dev
```

Nota: se agrego un `package.json` raiz con workspace hacia `web/`, asi que ahora `npm install` desde `B:\mundial` es valido. Tambien siguen funcionando los comandos entrando a `web/`:

```bash
cd web
npm install
npm run test
npm run build
npm run dev
```

Si `python scripts/update.py` quiere bajar datos de internet y solo queres probar la copia web:

```bash
python -c "import sys; sys.path.insert(0, r'B:/mundial/scripts'); import update; update.copy_web_data()"
```

## Estado git esperado

Cambios principales:

- `package.json`
- `README.md`
- `PENDIENTES_WEBAPP.md`
- `scripts/update.py`
- `web/`

No se hizo `git add`, commit ni push.

## Mejoras pendientes propuestas por Codex

Estas mejoras no venian cerradas en el plan original. Son ajustes que conviene hacer antes de considerar la web app lista para deploy publico.

### Hecho en vueltas anteriores

- Se agrego `package.json` en la raiz para que `npm install` desde `B:\mundial` sea valido y use workspace `web`.
- Se actualizaron los comandos del `README.md` para mostrar el flujo desde la raiz y tambien desde `web/`.
- Se agrego boton `Limpiar carga` en `/prode` para borrar draft local, resultados cargados y volver al primer partido.

### Hecho en la pasada de rediseño de `/mundial`

- Se rehizo `/mundial` para que no acumule todo hacia abajo.
- Ahora la experiencia funciona como pantallas:
  - Grupo A
  - Grupo B
  - ...
  - Grupo L
  - Mejores terceros
  - Dieciseisavos de final
  - Octavos de final
  - Cuartos de final
  - Semifinales
  - Final
- Cada pantalla limpia la anterior usando `AnimatePresence mode="wait"`.
- Se reemplazo la vista larga de bracket por fases separadas.
- Se redujo la estetica generica de grillas/cajitas:
  - fondo con textura sutil
  - layout mas editorial/deportivo
  - foco grande por fase
  - menos acumulacion visual
  - tablas y cruces mas contenidos
- Se mantuvieron los controles siempre visibles:
  - Autoplay
  - Siguiente
  - Saltear fase
  - Saltear todo
- Se mantiene `prefers-reduced-motion`.

Verificacion de esa pasada:

- `npm run test` desde `B:\mundial`: OK, 4 tests verdes en ese momento; hoy son 9 tests verdes.
- Chequeo sintactico con `esbuild` de rutas principales: OK.
- `npm run build` desde mi proceso de Codex fallo por permisos al escribir `web/.next/trace-build`:

```text
EPERM: operation not permitted, open 'B:\mundial\web\.next\trace-build'
```

Ese build conviene repetirlo desde tu terminal, que ya pudo ejecutar `npm install`.

### 1. Validar instalacion desde la raiz

Se agrego `package.json` en `B:\mundial` para que este flujo funcione:

```bash
npm install
npm run test
npm run build
npm run dev
```

Pendiente de verificar en tu terminal con permisos normales/admin:

- que `npm install` cree `package-lock.json`
- que npm instale dependencias del workspace `web`
- que `npm run build` ejecute Next desde `web`

### 2. Cambiar codec a `lz-string` real

Ahora el codec de `?p=` usa un formato compacto propio con base64-url. Funciona y tiene test de ida/vuelta, pero el plan original pidio `lz-string compressToEncodedURIComponent`.

Pendiente:

- importar `compressToEncodedURIComponent` y `decompressFromEncodedURIComponent`
- mantener el formato compacto interno `nombre|h0a0h1a1...`
- actualizar tests para garantizar compatibilidad
- decidir si se mantiene fallback para codigos viejos base64-url

### 3. Partir `MundialGroups.tsx`

`web/components/MundialGroups.tsx` fue reordenado internamente en funciones por pantalla, pero sigue estando en un solo archivo.

Sigue pendiente si queremos dejarlo mas mantenible:

Pendiente:

- extraer `PhaseRail`
- extraer `GroupReveal`
- extraer `ThirdsBoard`
- extraer `KnockoutBracket`
- extraer `RevealControls`

Esto haria mas facil revisar, testear y mejorar visualmente cada parte sin romper la ruta completa.

### 4. Mejorar el bracket visual — HECHO (2026-06-12, Claude)

Rediseño completo de las eliminatorias en `web/components/KnockoutBracket.tsx`:

- Desktop: cuadro de dos alas estilo `CUADRO.jpg` con CSS Grid de 17 columnas x 16 filas (sin SVG medido: conectores con pseudo-elementos punteados, geometria deterministica).
- Las alas se derivan del arbol `homeFrom`/`awayFrom` de `bracket.ts` (subarbol de SF 101 a la izquierda, SF 102 a la derecha), nada hardcodeado.
- Lineas que se encienden en dorado cruce por cruce, con chips de fase (8vos/4tos/Semis/Final) que pasan a dorado.
- Copa al centro (atenuada hasta la final) y `champion-mark` en el centro en la final.
- El bracket persiste entre rondas (key compartida en AnimatePresence) y revela cada ronda con stagger; ganador con overlay dorado, perdedor atenuado, ronda siguiente "nombrada", futuras como placeholder.
- Mobile (<=1080px): lista vertical de la ronda activa, mismo DOM filtrado por CSS.
- `RoundScreen` y el CSS de `.duel`/`.round-board` eliminados; `MundialGroups.tsx` quedo mas chico (avance parcial de la mejora #3: el knockout ya es componente propio).
- Verificado: tsc limpio, vitest 9, Playwright 16/16, screenshots desktop/mobile revisados (script auxiliar `web/e2e/shots.mjs`).

### 5. Agregar pruebas Playwright

Cuando `npm install` y `npm run dev` funcionen, agregar pruebas end-to-end.

Flujos minimos:

- abrir `/`
- ir a `/prode`
- importar `prode/prode_facu.json`
- confirmar 72/72
- navegar a `/mundial?p=...`
- verificar que el mismo `?p=` da el mismo campeon
- screenshot mobile 390px
- screenshot desktop

### 6. Pulir UX de carga del prode

Hecho:

- boton para limpiar draft
- mensajes claros si falta nombre o partidos

Pendiente:

- confirmacion antes de cambiar import por otro archivo
- resumen final por grupo antes de confirmar
- mejores estados vacios
- atajos de teclado mas completos

### 7. Robustecer ranking

Pendiente:

- estado vacio si no hay prodes
- mostrar desempates de forma explicita
- link copiable por jugador
- fecha de actualizacion de datos
- manejo de prodes incompletos o invalidos

### 8. Validar OG en deploy real

`/api/og` esta implementado, pero falta validarlo con build y Vercel.

Pendiente:

- confirmar que `next/og` funciona en build
- probar una URL real en OpenGraph preview
- decidir si conviene runtime `edge` o mantener `nodejs`

### 9. Documentar arquitectura

El README actual es minimo. Pendiente agregar:

- Python como fuente de datos
- `web/data` como snapshot deployable
- motor TS como port del Python
- como agregar prodes nuevos
- que archivos legacy no se deben borrar todavia
