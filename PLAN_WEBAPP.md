# SPEC EJECUTABLE — Web app "Prode Mundial 2026" (Next.js + Vercel)

> Spec autocontenida para ser ejecutada por un agente (Codex) SIN contexto previo.
> Repo: `B:\mundial`. Idioma de toda la UI: **español rioplatense**. Máquina: Windows 10;
> usar **bash** (Git Bash) para comandos — PowerShell está roto en esta máquina (error CET).
> Python 3.12 y Node 22 instalados.

---

## 1. CONTEXTO Y ESTADO ACTUAL

Existe un pipeline Python local que scrapea datos del Mundial 2026 y genera páginas HTML sueltas.
Se quiere reemplazar las páginas por **UNA web app Next.js deployada en Vercel**, manteniendo
Python solo como proveedor de datos. Sin base de datos en esta iteración (ya decidido).

Árbol actual relevante:

```
B:\mundial\
  scripts\            # Python: NO romper, solo agregar el paso de copia (Sprint 5)
    teams.py          # 12 grupos (A-L), 48 selecciones, nombres ES, alias
    bracket.py        # bracket oficial FIFA R32->Final + standings + terceros (FUENTE DE VERDAD para portar)
    predict.py        # modelo Elo->Poisson (constantes abajo)
    game.py           # sorteo eliminatorias con semilla + scoring (FUENTE DE VERDAD para portar)
    update.py         # orquestador del pipeline
  data\
    fixture.json      # 72 partidos con resultados reales y fairplay
    team_profiles.json# elo + forma por selección
    predictions.json  # predicciones del modelo por partido pendiente
    model_picks.json  # picks del modelo congelados pre-partido
  prode\
    prode_facu.json   # prode real del usuario (player "facu", 72 resultados)
  cuadro.jpg          # REFERENCIA VISUAL del bracket a construir (dos alas + copa al centro)
  mundial2026.html, prode.html, juego.html   # legado: NO borrar, dejan de evolucionar
```

### Esquemas de datos (leer tal cual, no inventar campos)

`data/fixture.json`:
```json
{ "updated": "2026-06-12T...", "source": "wikipedia",
  "fairplay": {"Mexico": -5, ...},            // deducción FIFA, más negativo = peor
  "matches": [ {
    "match_id": "2026-A-01", "group": "A",
    "home": "Mexico", "away": "South Africa",  // nombres canónicos EN
    "home_es": "México", "away_es": "Sudáfrica",
    "date": "2026-06-11", "time": "13:00",
    "venue": "Estadio Azteca , Mexico City", "venue_country": "Mexico",
    "status": "played" | "pending", "score": [2,0] | null } ] }
```

`data/team_profiles.json`: `{"profiles": {"Argentina": {"elo": 2187.3, "group": "J",
"form_last10": [W,D,L], "avg_gf_2y": 2.1, "avg_gc_2y": 0.6, "fifa_rank": 1|null, ...}}}`

`data/predictions.json`: `{"predictions": {"2026-A-02": {"p1": 49, "px": 26, "p2": 25,
"lambda_home": 1.38, "lambda_away": 1.05, "rho": 1.1, "score_pred": [1,0],
"favorite": "...", "confidence": "alta|media-alta|media|baja", ...}}}`

`data/model_picks.json`: `{"2026-A-02": [1,0], ...}` (pick del modelo ANTES de jugarse; nunca se pisa).

Prode de jugador (`prode/prode_facu.json` y los que manden los amigos):
```json
{ "player": "facu", "created": "...", "results": {"2026-A-01": [2,0], ... 72 entradas} }
```

---

## 2. REGLAS DE NEGOCIO (portar EXACTO de Python a TypeScript)

### 2.1 Posiciones de grupo y terceros (`scripts/bracket.py`)
- Tabla: 3 pts victoria, 1 empate. Orden: **pts → dif. gol → goles a favor → fair play
  (deducción menos negativa primero) → orden alfabético** (determinístico, sin azar).
- Clasifican 1° y 2° de cada grupo + los **8 mejores terceros** (mismo criterio de orden).

### 2.2 Bracket oficial FIFA (verificado contra Wikipedia; NO cambiar)
16avos (partido, local, visitante): W=ganador, R=segundo, T=tercero con cupo de grupos:
```
73: R-A vs R-B      | 74: W-E vs T(ABCDF) | 75: W-F vs R-C      | 76: W-C vs R-F
77: W-I vs T(CDFGH) | 78: R-E vs R-I      | 79: W-A vs T(CEFHI) | 80: W-L vs T(EHIJK)
81: W-D vs T(BEFIJ) | 82: W-G vs T(AEHIJ) | 83: R-K vs R-L      | 84: W-H vs R-J
85: W-B vs T(EFGIJ) | 86: W-J vs R-H      | 87: W-K vs T(DEIJL) | 88: R-D vs R-G
```
Asignación de terceros: emparejamiento por **backtracking** de los 8 grupos clasificados a los
8 cupos T (probar el slot con menos opciones primero). Ver `assign_thirds()` en bracket.py.
Octavos: 89=W74vW77, 90=W73vW75, 91=W76vW78, 92=W79vW80, 93=W83vW84, 94=W81vW82, 95=W86vW88, 96=W85vW87.
Cuartos: 97=W89vW90, 98=W93vW94, 99=W91vW92, 100=W95vW96. Semis: 101=W97vW98, 102=W99vW100. Final: 104=W101vW102.
Sedes/países por partido: copiar literal de las listas `R16/QF/SF/FINAL` de bracket.py
(importa el país para la localía: Azteca/BBVA=Mexico, BMO/BC Place=Canada, resto=United States).

### 2.3 Modelo de cruce (de `scripts/predict.py` / `game.py`)
```
HOME_ADV=85, RHO=1.10, MAX_G=8, MIN_LAMBDA=0.18, BASE_TOTAL=2.55
diff = elo_h - elo_a + 85*(home==país_sede) - 85*(away==país_sede)
we   = 1/(1+10^(-diff/400))
atk  = (gf_h + gc_a + gf_a + gc_h)/2          // promedios avg_*_2y de team_profiles
total= clamp(0.5*2.55 + 0.5*atk, 1.8, 3.6)
λh = max(0.18, total*we) ; λa = max(0.18, total*(1-we))
matriz 9x9 Poisson independiente, diagonal *1.10, renormalizada
```

### 2.4 Sorteo de eliminatorias ("el destino", de `game.py: ko_draw`)
- Muestrear un marcador de la matriz. Si empate → penales: gana home con prob `we`.
- Mostrar marcador (con sufijo ` (pen)` si hubo) y prob. del ganador `p1 + px*we` (o complemento).
- **PRNG sembrado y reproducible**: semilla = hash de `nombre + JSON.stringify(results ordenado)`.
  En TS usar xmur3 (hash) + mulberry32 (PRNG). NO debe coincidir con Python (imposible), pero
  SÍ debe dar siempre lo mismo para el mismo prode entre corridas/navegadores.

### 2.5 Puntaje del prode
- Por partido jugado real: **exacto = 3 pts**, **acierto 1X2 (sin exacto) = 1 pt**.
- Se puntúan TODOS los jugados contra lo que puso el jugador (los pre-cargados también; juego de confianza).
- Jugador virtual "🤖 Modelo": sus picks = `model_picks.json` (si un partido no tiene pick, no puntúa).
- Futuro (NO implementar ahora, dejar constantes): +2 por clasificado real, +10 campeón.

---

## 3. DECISIONES UX/UI (obligatorias)

- **Mobile-first** (390px primero). Estética: dark elegante ya usada en el proyecto:
  fondo `#0a1020`, cards `#121b33`, líneas `#22304f`, texto `#e8edf8`, acentos cian `#22d3ee`,
  violeta `#6366f1`, dorado `#fbbf24`, ok `#34d399`. Fuentes Google: Sora (títulos) + Inter (texto).
  Colores por grupo (chips): A #dc2626, B #ea580c, C #16a34a, D #2563eb, E #7c3aed, F #db2777,
  G #0d9488, H #ca8a04, I #4f46e5, J #0891b2, K #9333ea, L #b91c1c.
- **Carga carta por carta**: un partido por pantalla, chips rápidos (0-0, 1-0, 2-0, 2-1, 1-1, 3-0, 3-1 + stepper manual),
  Enter/swipe avanza, progreso "Partido 23/72", mini-tabla animada al completar cada grupo,
  badge `real: x-x` en jugados (igual editables). Toggle "modo planilla" (grilla por grupo).
  Botón "completar lo que falta con el 🤖 modelo" (usa `score_pred`).
- **Un viaje continuo**: ruta `/mundial?p=<código>` con rail de fases
  (Grupos → 16avos → 8vos → 4tos → Semis → Final). Sin cambios de página entre fases.
- **Revelación de grupos**: grupo por grupo (A→L): cards de partido con count-up del marcador,
  tabla que se reordena animada (Framer Motion layout), 1° y 2° se encienden en verde;
  cierre con suspenso de los 8 mejores terceros.
- **El cuadro** (referencia `cuadro.jpg`): desktop = SVG dos alas (8 llaves por lado) convergiendo
  a la copa 🏆 al centro, conectores punteados; mobile = vista vertical fase por fase.
  Revelación cruce por cruce: aparece el marcador, el ganador "viaja" a su caja siguiente y la
  **línea conectora se enciende** (stroke-dashoffset animado + glow). Campeón: canvas-confetti.
- **Controles SIEMPRE visibles**: ▶ autoplay / siguiente / saltear fase / saltear todo.
  `prefers-reduced-motion` ⇒ todo resuelto al instante.
- **Compartir**: el prode viaja comprimido (lz-string `compressToEncodedURIComponent`) en `?p=`
  (query, NO hash — necesario para OG). Botones Web Share API + copiar link.

---

## 4. SPRINTS (ejecutar en orden; cada uno termina con su verificación en verde)

### Sprint 1 — Repo + scaffold + motor TS
1. `git init` en B:\mundial. `.gitignore`: `data/history.csv`, `__pycache__/`, `web/node_modules/`, `web/.next/`, `*.pyc`.
   Commit inicial de lo existente.
2. `npx create-next-app@latest web` → TypeScript, Tailwind, App Router, sin src-dir (o con, ser consistente).
   `npm i framer-motion lz-string canvas-confetti` + `npm i -D vitest tsx @types/canvas-confetti`.
3. Copiar `data/{fixture,team_profiles,predictions,model_picks}.json` → `web/data/` y `prode/*.json` → `web/data/prodes/`.
4. Portar a `web/lib/` (módulos puros, sin React): `teams.ts`, `standings.ts`, `bracket.ts`,
   `model.ts`, `draw.ts`, `scoring.ts`, `prode-codec.ts` (encode/decode del prode con lz-string;
   formato compacto: `nombre|h0a0h1a1...` en orden fijo de match_ids ordenados).
5. **Verificación (paridad con Python como oráculo):** test vitest que, con los resultados del
   prode `web/data/prodes/prode_facu.json` completados con resultados reales:
   - las posiciones de los 12 grupos coinciden con las que imprime Python
     (correr `cd B:\mundial && python -c "..."` una vez y hardcodear el snapshot esperado en el test);
   - los 16 cruces de R32 (equipos local/visitante) coinciden;
   - el puntaje de "facu" da exactamente el de `juego.html` actual (exact=1, outcome=0, 3 pts);
   - `decode(encode(prode)) === prode`.

### Sprint 2 — Landing + carga del prode
- `/` (landing): hero con título, explicación corta del juego, CTA "Armá tu prode",
  lista "tus prodes" desde localStorage (nombre + campeón si ya se sorteó + link).
- `/prode`: modo carta por carta + modo planilla (sección 3). Import de archivo `prode_*.json`.
  Estado en localStorage (autosave). Al completar 72: pantalla de confirmación con nombre →
  guarda y navega a `/mundial?p=<código>`.
- **Verificación:** cargar un prode completo a mano en dev; recargar a mitad de camino (no pierde nada);
  importar `prode_facu.json` y ver 72/72.

### Sprint 3 — `/mundial` fase Grupos (la revelación)
- Decodifica `?p=`; si falta o es inválido → redirige a `/prode` con mensaje.
- Secuencia de revelación de grupos según sección 3, con el rail de fases arriba.
- **Verificación:** flujo completo con autoplay; saltear fase; saltear todo; reduced-motion.

### Sprint 4 — `/mundial` fases eliminatorias (el cuadro)
- Continúa en la misma ruta. Bracket SVG desktop dos alas (layout fijo: partidos 73-80 ala
  izquierda de arriba a abajo, 81-88 ala derecha; 89-92 izq / 93-96 der; 97,99 izq / 98,100 der;
  semis a los lados de la copa; final al centro) + variante mobile vertical.
- Sorteo con `draw.ts` (semilla del prode ⇒ mismo destino siempre). Revelación cruce por cruce
  con líneas que se encienden; campeón + confetti; CTA final "Compartir mi Mundial".
- **Verificación:** mismo `?p=` en dos navegadores ⇒ MISMO campeón y marcadores; skip funciona
  en cada fase; se ve bien en 390px y en desktop.

### Sprint 5 — Ranking, OG y deploy
- `/ranking`: jugadores = `web/data/prodes/*.json` + 🤖 Modelo (model_picks). Tabla: pos, nombre,
  exactos, 1X2, puntos, su campeón (sorteado con su semilla), link a su `/mundial?p=…`.
- `/api/og` (edge, @vercel/og): tarjeta 1200x630 "El Mundial de <nombre> — 🏆 <campeón>" leyendo `?p=`.
  Meta tags OG/Twitter en `/mundial` vía `generateMetadata`.
- Python: agregar paso 10 a `scripts/update.py` que copie `data/*.json` → `web/data/` y
  `prode/*.json` → `web/data/prodes/` (función simple con shutil; no tocar lo demás).
- Deploy: `vercel` CLI o conectar repo GitHub (guiar al usuario para crear el repo remoto y la
  cuenta Vercel; el proyecto apunta a `web/` como root). `npm run build` debe pasar limpio antes.
- **Verificación:** build sin errores; deploy accesible desde el celular; preview OG en
  https://www.opengraph.xyz con un link `?p=` real; flujo diario documentado en README:
  `python scripts/update.py && git add -A && git commit -m "datos" && git push` ⇒ redeploy.

### Fuera de alcance (NO hacer ahora)
Supabase/usuarios (próxima iteración), puntaje de eliminatorias reales (julio),
bonus +2/+10 (solo dejar las constantes), sonido.
