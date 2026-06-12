# Prode Mundial 2026

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
- `prode/*.json`

a `web/data/` para el deploy.

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

- `/` landing y prodes guardados localmente
- `/prode` carga carta por carta o planilla
- `/mundial?p=<codigo>` revelación de grupos y cuadro
- `/ranking` tabla de jugadores y modelo
