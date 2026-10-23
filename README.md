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

## Estructura

```
docs/            plan maestro, requisitos, registro de riesgos, ADR
research/        preregistration/, trials.csv, notebooks/ (sin datos crudos)
src/trading/     data/, features/, signals/, risk/, decision/, execution/, audit/
tests/           espejo de src/
ops/             runbook.md, incidents/
```
