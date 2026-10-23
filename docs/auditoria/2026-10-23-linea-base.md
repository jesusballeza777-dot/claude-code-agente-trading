# Línea base: 23-oct-2026

**Commit medido:** `e6aa422` (rama `claude/maestro-v2-phase0-foundations-wp6t5d`) · **Objetivo:** dejar constancia del estado antes de la auditoría y de las olas 1-7. No se cambió nada para medirla.

## Herramientas disponibles en el entorno de desarrollo

| Herramienta | Estado | Notas |
|---|---|---|
| Python 3.12 + uv 0.11.32 | disponible | `uv sync --locked` limpio |
| Node 22.22.0, npm 10.9.4, pnpm 10.28.0 | disponible | registro de npm accesible |
| Playwright + Chromium | disponible | navegadores en `/opt/pw-browsers` |
| Docker 29.9.1 + Compose v5.6.0 | disponible | el daemon hay que arrancarlo a mano en este contenedor; se probó TimescaleDB 2.17.2 (PostgreSQL 16) en contenedor con éxito |
| PostgreSQL 16 (cliente y servidor locales) | disponible | sin la extensión TimescaleDB fuera de Docker |
| Pango/Cairo (para PDF con WeasyPrint) | disponible | WeasyPrint no instalado aún |
| SDK de Android | **no disponible** | la app Android se compila en GitHub Actions |
| Archivo público de Binance | disponible vía `s3-ap-northeast-1.amazonaws.com/data.binance.vision` | `data.binance.vision` directo está bloqueado por el proxy; los ficheros y sus `.CHECKSUM` coinciden |
| API pública de Binance (`fapi.binance.com`) | **bloqueada** | no hace falta: se usa el archivo |
| Banxico SIE (tipo FIX) | **bloqueado** desde aquí | además la API requiere un token: columna "por completar" en los reportes |
| support.claude.com | disponible | usado para verificar los créditos de API de Max |

## Salida real de las comprobaciones

```
$ uv sync --locked
Resolved 28 packages in 97ms
Checked 27 packages in 651ms

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
65 files already formatted

$ uv run mypy
pyproject.toml: note: unused section(s): module = ['trading.execution.*']
Success: no issues found in 34 source files

$ uv run pytest --cov
........................................................................ [ 75%]
..............................................                           [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.3-final-0 ________________

Name                                   Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------------
src/trading/__init__.py                    0      0      0      0   100%
src/trading/audit/__init__.py              2      0      0      0   100%
src/trading/audit/records.py             146      0     30      0   100%
src/trading/data/__init__.py               0      0      0      0   100%
src/trading/decision/__init__.py           0      0      0      0   100%
src/trading/execution/__init__.py          0      0      0      0   100%
src/trading/features/__init__.py           0      0      0      0   100%
src/trading/reporting/__init__.py          5      0      0      0   100%
src/trading/reporting/decisions.py        41      0      0      0   100%
src/trading/reporting/performance.py      54      0      8      0   100%
src/trading/reporting/review.py           58      0     18      0   100%
src/trading/reporting/tax.py              79      0     10      0   100%
src/trading/risk/__init__.py               6      0      0      0   100%
src/trading/risk/engine.py               154      0     50      0   100%
src/trading/risk/limits.py               127      0     52      0   100%
src/trading/risk/liquidation.py           23      0      6      0   100%
src/trading/risk/models.py               139      0     32      0   100%
src/trading/risk/sizing.py                34      0      8      0   100%
src/trading/settings.py                    2      0      0      0   100%
src/trading/signals/__init__.py            0      0      0      0   100%
----------------------------------------------------------------------------------
TOTAL                                    870      0    214      0   100%
190 passed in 9.14s

$ coverage report --include="src/trading/risk/*" --fail-under=95
src/trading/risk/sizing.py           34      0      8      0   100%
-----------------------------------------------------------------------------
TOTAL                               483      0    148      0   100%
```

## Lectura

- 190 tests en verde; cobertura de ramas del 100% en todo `src/trading` (umbral del CI: 95% en `risk/`).
- La nota de mypy sobre `trading.execution.*` es esperable: el paquete aún no tiene submódulos.
- Esta línea base no dice nada sobre la **corrección** de lo que mide: eso es la auditoría (`2026-10-23-auditoria.md`).
