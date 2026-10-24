# claude-code-agente-trading

Agente de trading cripto con Claude: BTC, ETH y pocas alts líquidas en Binance spot y perpetuos USDⓈ-M.
La rentabilidad no se da por supuesta; es la hipótesis que el sistema tiene que demostrar.
No es asesoría financiera, legal ni fiscal.

**Fase actual (ADR-012):** F0 cerrada; F1 pendiente del propietario; en curso F2, F3 con datos públicos (sin claves),
F4 sobre 2020-2024 y el Centro de Mando. La ejecución real está desactivada (`LIVE_TRADING=false`).

## Documentos rectores

- [`CLAUDE.md`](CLAUDE.md): reglas permanentes (secretos, ejecución real, veto del motor de riesgo, pre-registro).
- [`docs/plan-maestro-v2.1.md`](docs/plan-maestro-v2.1.md): plan maestro vigente (el [v2](docs/plan-maestro-v2.md) queda como histórico).
- [`docs/estado-y-faltantes.md`](docs/estado-y-faltantes.md): qué está hecho y verificado, qué falta y tus pendientes en orden.
- [`docs/resultados/f4-analisis.md`](docs/resultados/f4-analisis.md): resultados de la F4 (2020-2024) y opciones para seguir.
- [`docs/presupuesto.md`](docs/presupuesto.md): presupuesto mensual (fuente única).
- [`docs/auditoria/`](docs/auditoria/): línea base y auditoría del 23-oct-2026.
- `docs/requirements.md`, `docs/adr/`, `docs/risk_register.md`: requisitos, decisiones de arquitectura y riesgos.
- `research/preregistration/`: pre-registro de hipótesis antes de cualquier backtest; `research/trials.csv`: todas las corridas.
- [`docs/f1-verificacion-plataforma.md`](docs/f1-verificacion-plataforma.md): comprobaciones que hace el propietario en Binance, Hyperliquid y Anthropic (F1).
- [`ops/secrets.md`](ops/secrets.md): puesta en marcha de SOPS/age para los secretos.
- [`docs/app/especificacion.md`](docs/app/especificacion.md): la app Android (resumen, decisiones, aprendizaje, controles y reportes fiscales).
- [`docs/capturas/`](docs/capturas/): capturas del Centro de Mando (oscuro, claro y móvil).

## Estructura

```
docs/            plan maestro, requisitos, riesgos, ADR, resultados, capturas
research/        preregistration/, trials.csv, results/ (una ficha JSON por corrida)
src/trading/     data/ (F3), features/, signals/ (H1, H2, H4), backtest/ (F4), risk/, api/ (Centro de Mando),
                 audit/, reporting/ (PDF, Excel, contador), decision/, execution/
tests/           espejo de src/
app/web/         Centro de Mando: React + Vite + TypeScript (Vitest y Playwright)
app/android/     app Android: cliente nativo del Centro de Mando (Kotlin), compilada en CI
ops/             runbook.md, incidents/, secrets.md, docker/ (imágenes del Centro de Mando)
data/            datos públicos descargados (no se versiona)
```

## Arrancar el Centro de Mando en local

El Centro de Mando es de **solo lectura respecto al dinero**: no envía órdenes, no activa `LIVE_TRADING`,
no crea claves ni cambia límites (ADR-015). Sin datos descargados, las vistas de mercado salen rotuladas como demo.

**Opción A: todo con Docker** (base de datos, backend y app):

```bash
CODE_COMMIT=$(git rev-parse --short=12 HEAD) docker compose up --build
# abre http://127.0.0.1:8080
```

Solo escucha en `127.0.0.1` y en local no pide contraseña. Los datos de `data/` se montan de solo lectura;
las notas del diario y el historial de reportes viven en el volumen `app-state`.

**Opción B: desarrollo** (recarga en caliente):

```bash
uv sync --locked
TRADING_API_AUTH=disabled uv run python -m trading.api      # API en 127.0.0.1:8000
cd app/web && npm ci && npm run dev                          # app en 127.0.0.1:5173 (proxy a la API)
```

Para que la API sirva la app compilada en `127.0.0.1:8000`: `cd app/web && npm run build`.

### App de celular

- **Android (APK):** [`app/android/README.md`](app/android/README.md). Muestra el Centro de Mando completo con bloqueo
  biométrico; se conecta por cable USB (`adb reverse tcp:8080 tcp:8080`) o por Tailscale. ADR-018.
- **Sin APK:** abre la dirección del Centro de Mando en el navegador del celular y usa "Instalar app" / "Añadir a la pantalla de inicio".
- **En vivo:** la página `/en-vivo` muestra qué piezas existen y trabajan, y qué ha pasado; se actualiza cada 5 s.

### Datos públicos y backtests (sin claves)

```bash
uv run python -m trading.data.f3          # descarga data.binance.vision 2020-2024 con verificación SHA-256
docker compose up -d db && uv run python -m trading.data.timescale   # opcional: carga en TimescaleDB
uv run python -m trading.backtest.f4      # corridas pre-registradas; anota cada una en research/trials.csv
```

El holdout (2025-01-01 → hoy) está sellado: el código se niega a leerlo sin la autorización firmada del propietario.

## Acceso seguro desde el celular (VPS)

Nunca publiques el puerto en internet (ADR-015). El servidor escucha solo en `127.0.0.1` y se llega a él por una red privada.

1. **Credenciales, en tu ordenador** (nadie más las ve):
   ```bash
   uv run python -m trading.api.credentials        # pide la contraseña sin mostrarla
   sops secrets/centro-de-mando.sops.yaml           # pega las tres líneas que imprimió; queda cifrado
   ```
   Da de alta el TOTP en tu app de autenticación con la línea `otpauth://` y limpia la terminal.
2. **Arranque en el VPS con autenticación** (los secretos solo existen en memoria):
   ```bash
   TRADING_API_AUTH=on TRADING_API_SECURE_COOKIE=1 \
     sops exec-env secrets/centro-de-mando.sops.yaml 'docker compose up -d --build'
   ```
   Si falta un secreto, el backend se niega a arrancar.
3. **Acceso privado:**
   - **Tailscale** (recomendado): instala Tailscale en el VPS y en el celular, y en el VPS ejecuta
     `tailscale serve --bg 8080`. La app queda en `https://<vps>.<tu-red>.ts.net`, solo para tus dispositivos.
   - **Túnel SSH** (alternativa): `ssh -L 8080:127.0.0.1:8080 usuario@vps` y abre `http://127.0.0.1:8080`
     (en ese caso arranca sin `TRADING_API_SECURE_COOKIE=1`, porque no hay HTTPS).

Por verificar en un VPS real: el comando de `tailscale serve` y el flujo completo con `sops exec-env`.

## Desarrollo

Requisitos: [uv](https://docs.astral.sh/uv/) (descarga Python 3.12 si hace falta) y Node.js 22 para `app/web`.

```bash
uv sync --locked                 # entorno exacto del lockfile
uv run pre-commit install        # ganchos: gitleaks, higiene, ruff y mypy
uv run pytest --cov              # tests con cobertura (los de TimescaleDB necesitan `docker compose up -d db`)
uv run coverage report --include="src/trading/risk/*" --fail-under=95
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run pip-audit --skip-editable # vulnerabilidades conocidas en dependencias

cd app/web
npm ci && npm run typecheck && npm test && npm run build
npm run e2e                      # Playwright + axe contra la API real (arranca el backend solo)
CAPTURAS=1 npx playwright test e2e/capturas.spec.ts   # regenera docs/capturas/
```

El workflow `.github/workflows/ci.yml` ejecuta todo lo anterior en cada push y pull request: lint, tipos, tests con
TimescaleDB, cobertura (≥95% riesgo; ≥80% API y reportes), pip-audit y npm audit, la app web con sus E2E, las imágenes
Docker con una prueba de humo, la app Android y gitleaks sobre el historial completo.

### Herramientas y por qué (CLAUDE.md: justificar cada dependencia)

| Herramienta | Problema que resuelve |
|---|---|
| uv + `uv.lock` | Entorno reproducible con versiones y hashes fijados |
| pytest | Tests deterministas del código que calcula y limita |
| pytest-cov | Medir la cobertura ≥95% exigida al motor de riesgo (CLAUDE.md regla 4) |
| hypothesis | Pruebas de propiedades: invariantes del motor de riesgo para miles de entradas, no solo los casos escritos a mano |
| ruff | Lint (incluidas reglas de seguridad `S` y de fechas sin zona horaria `DTZ`) y formato |
| mypy | Tipos; strict en `risk/`, `execution/`, `audit/` y `reporting/` |
| pre-commit | Ejecutar gitleaks, ruff y mypy antes de cada commit |
| gitleaks | Bloquear secretos en commits y en el historial (CLAUDE.md regla 1) |
| pip-audit · npm audit | Avisar de vulnerabilidades conocidas en las dependencias |
| polars | Leer y escribir Parquet de la F3 sin cargar todo en memoria (ADR-016) |
| psycopg | Cargar los datos en TimescaleDB (ADR-016) |
| FastAPI + uvicorn | API de solo lectura del Centro de Mando (ADR-014, ADR-015) |
| Jinja2 + WeasyPrint · openpyxl | Reportes PDF y Excel descargables (ADR-017) |
| React, Vite, TypeScript, Tailwind | App web del Centro de Mando; Lightweight Charts para velas y Recharts para métricas |
| Vitest · Playwright + axe | Tests de componentes, E2E de los flujos y accesibilidad |

El motor de riesgo sigue siendo código puro: usa solo la biblioteca estándar.
