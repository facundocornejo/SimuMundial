# Pendientes web app Prode Mundial 2026

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
