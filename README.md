# claude-code-agente-trading

Agente de trading cripto con Claude: BTC, ETH y pocas alts líquidas en Binance spot y perpetuos USDⓈ-M.
La rentabilidad no se da por supuesta; es la hipótesis que el sistema tiene que demostrar.
No es asesoría financiera, legal ni fiscal.

**Fase actual:** F0 (alcance y gobernanza) + cimientos de F2. No hay código que se conecte a exchanges
y la ejecución real está desactivada (`LIVE_TRADING=false`).

## Documentos rectores

- [`CLAUDE.md`](CLAUDE.md): reglas permanentes (secretos, ejecución real, veto del motor de riesgo, pre-registro).
- [`docs/plan-maestro-v2.md`](docs/plan-maestro-v2.md): plan maestro v2 y decisiones del propietario.
- `docs/requirements.md`, `docs/adr/`, `docs/risk_register.md`: requisitos, decisiones de arquitectura y riesgos.
- `research/preregistration/`: pre-registro de hipótesis antes de cualquier backtest.
- [`docs/f1-verificacion-plataforma.md`](docs/f1-verificacion-plataforma.md): comprobaciones que hace el propietario en Binance, Hyperliquid y Anthropic (F1).
- [`ops/secrets.md`](ops/secrets.md): puesta en marcha de SOPS/age para los secretos.
- [`docs/app/especificacion.md`](docs/app/especificacion.md): la app Android (resumen, decisiones, aprendizaje, controles y reportes fiscales).

## Estructura

```
docs/            plan maestro, requisitos, registro de riesgos, ADR
research/        preregistration/, trials.csv, notebooks/ (sin datos crudos)
src/trading/     data/, features/, signals/, risk/, decision/, execution/, audit/, reporting/
tests/           espejo de src/
ops/             runbook.md, incidents/, secrets.md
app/android/     app Android de control (Kotlin + Compose), compilada en CI
```

## Desarrollo

Requisitos: [uv](https://docs.astral.sh/uv/) y Python 3.12 (uv lo descarga si no está instalado).

```bash
uv sync --locked                 # entorno exacto del lockfile
uv run pre-commit install        # ganchos: gitleaks, higiene, ruff y mypy
uv run pytest --cov              # tests con cobertura
uv run coverage report --include="src/trading/risk/*" --fail-under=95
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

El workflow `.github/workflows/ci.yml` ejecuta todo lo anterior en cada push y pull request, y además
escanea el historial completo con gitleaks.

### Herramientas y por qué (CLAUDE.md: justificar cada dependencia)

| Herramienta | Problema que resuelve |
|---|---|
| uv + `uv.lock` | Entorno reproducible con versiones y hashes fijados |
| pytest | Tests deterministas del código que calcula y limita |
| pytest-cov | Medir la cobertura ≥95% exigida al motor de riesgo (CLAUDE.md regla 4) |
| hypothesis | Pruebas de propiedades: invariantes del motor de riesgo para miles de entradas, no solo los casos escritos a mano |
| ruff | Lint (incluidas reglas de seguridad `S` y de fechas sin zona horaria `DTZ`) y formato |
| mypy | Tipos; strict en `risk/` y `execution/` (CLAUDE.md) |
| pre-commit | Ejecutar gitleaks, ruff y mypy antes de cada commit |
| gitleaks | Bloquear secretos en commits y en el historial (CLAUDE.md regla 1) |

No hay dependencias de runtime: el motor de riesgo usa solo la biblioteca estándar.
