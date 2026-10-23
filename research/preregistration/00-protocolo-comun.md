# Protocolo común de investigación (F4)

- **Versión:** v1 · **Estado:** FUSIONADO en `main` el 23-oct-2026 (PR #1)
- **Fecha:** 2026-10-23 · **Aplica a:** H1, H2, H4 (H3 aplazada)
- **Fuentes:** plan maestro v2 §3, §5; CLAUDE.md reglas 6 y 7; ADR-001, ADR-004, ADR-007
- **Aprobado por:** propietario, 23-oct-2026
- **Commit de fusión:** `4614d659247e57ef6f01614b4986c125fe5468f9`
- **Quién decidió:** el propietario delegó las decisiones abiertas en Claude el 23-oct-2026 ("avanza y termina el trabajo"). Cada decisión lleva su justificación; el propietario puede cambiar cualquiera **antes** de fusionar, nunca después de ver resultados.

Lo que el plan ya decide se marca **[fijado]**. Ninguna decisión de este documento se ha tomado mirando resultados de backtest: no se ha ejecutado ninguno.

## 1. Lo que ya está fijado

- **[fijado]** Comisiones de futuros y funding incluidos en **todos** los backtests (plan §5).
- **[fijado]** Holdout sellado: 2025-01-01 → fecha del gate. Se abre una sola vez, en el gate de la F4, con aprobación explícita (CLAUDE.md regla 7).
- **[fijado]** Señales solo sobre velas cerradas de 4h o 1d con límites en UTC; entrada después del cierre de la vela de señal (ADR-004).
- **[fijado]** Toda ejecución se anota en `research/trials.csv` (CLAUDE.md regla 6).
- **[fijado]** Cortos solo en estrategias validadas en ambas direcciones (plan §3).
- **[fijado]** Gate de la F4 (plan §5):
  1. ≥200 operaciones en walk-forward fuera de muestra.
  2. Esperanza neta con IC90% > 0.
  3. PF neto ≥1.25.
  4. DSR ≥0.90 y PBO ≤0.30.
  5. MaxDD p95 de Monte Carlo ≤25%.
  6. Sigue rentable con costes ×1.5 y parámetros ±20%.
  7. Positiva en ≥2 de 3 regímenes.
  8. Ningún mes aporta más del 30% del beneficio.
  9. En el holdout 2025-26, esperanza > 0 y PF ≥1.1.

## 2. Hechos verificados que condicionan las decisiones

Comprobados el 23-oct-2026 leyendo solo el listado de ficheros del archivo público `data.binance.vision`, sin descargar precios ni mirar resultados:

| Dato | Primer fichero disponible | Estado |
|---|---|---|
| Velas y funding de perpetuos con margen en USDT (BTCUSDT, ETHUSDT) | 2020-01 | **confirmado** |
| Velas y funding de perpetuos con margen en USDC (BTCUSDC, ETHUSDC) | 2024-01 | **confirmado** |
| Open interest (métricas) BTCUSDT | 2020-09-01 | **confirmado** |
| Open interest (métricas) ETHUSDT | 2021-12-01 | **confirmado** |
| Comisión taker estándar (VIP 0) de USDⓈ-M: 0.05% por lado | — | **estimado** (fuentes secundarias); por verificar en F1 |
| Nocional mínimo de orden: BTCUSDT 100 USDT; resto sin confirmar | — | **estimado**; por verificar en F1 |
| Que el archivo conserva los contratos deslistados (necesario para H2) | — | **por verificar** en F3 |

## 3. Supuestos de ejecución en el backtest

| Elemento | Regla |
|---|---|
| Precio de entrada | Apertura de la vela siguiente a la de señal, orden a mercado (taker) más slippage |
| Stop alcanzado dentro de la vela | Al precio del stop más slippage de stop; si la vela abre más allá del stop (gap), al precio de apertura más slippage de stop |
| Stop y otra salida en la misma vela | Se ejecuta el stop (supuesto conservador) |
| Salida por regla | Apertura de la vela siguiente a la que la genera, más slippage |
| Funding | Tasa histórica real en cada liquidación mientras la posición está abierta, con el intervalo de liquidación vigente en esa fecha |
| Tamaño | Lo calcula el motor de riesgo de `src/trading/risk/` con los límites de F7-F8 (C-12) |
| Apalancamiento configurado en el exchange | 3×, margen aislado (C-20) |
| Nocional mínimo | Si el tamaño por riesgo queda por debajo del mínimo del contrato, la operación **no se ejecuta** y se registra como "no ejecutable"; nunca se aumenta el tamaño (C-19) |
| Vetos del motor | Una señal vetada no es una operación; se registra con el motivo del veto |

## 4. Decisiones

| ID | Decisión | Justificación |
|---|---|---|
| C-01 | **Backtest con perpetuos con margen en USDT.** La operación real usa el contrato que confirme la F1; la diferencia USDT/USDC se trata como coste y se mide en la F7 | Confirmado: con margen en USDC solo hay histórico desde 2024-01, un año antes del holdout |
| C-02 | **Ambas direcciones en perpetuos** | Una sola estructura de costes y un solo instrumento por activo |
| C-03 | **Periodo de investigación: 2020-01-01 → 2024-12-31** | Primer mes completo del archivo de perpetuos; no se inventa funding para años sin perpetuo |
| C-04 | **Parámetros fijados a priori en cada pre-registro, sin optimización.** Todo el periodo posterior al calentamiento de los indicadores es fuera de muestra porque nada se ajusta con datos; los resultados se informan por ventanas semestrales | Con 5 años, reoptimizar dejaría ≈3 años fuera de muestra y haría inalcanzables las 200 operaciones. Fijar a priori elimina la selección, que es la fuente principal de sobreajuste |
| C-05 | **Regímenes por tendencia de BTC.** Con el cierre diario del par spot BTCUSDT (solo para etiquetar; histórico desde 2017): alcista si cierre > media de 200 días y la media sube respecto a 20 días antes; bajista si cierre < media y la media baja; lateral el resto. Cada operación toma el régimen del día de entrada. Un régimen con menos de 20 operaciones **no cuenta como positivo** | Definición objetiva y calculable sin mirar resultados; la regla de 20 operaciones evita aprobar un régimen por azar |
| C-06 | **Parámetros ±20%:** cada variante que mueve un parámetro un 20% arriba o abajo (uno cada vez) mantiene esperanza neta > 0. **Costes ×1.5:** el límite inferior del IC90% de la esperanza sigue > 0 | Exigente pero alcanzable; la prueba de costes es la más relevante para operar con poco capital |
| C-07 | **Esperanza en múltiplos de R netos de costes** (R = riesgo planificado de la operación) | Coincide con el tamaño por riesgo del motor |
| C-08 | **IC90% por bootstrap percentil**, 10,000 remuestreos, bilateral; pasa si el percentil 5 > 0. Semilla fija: 20261023 | No supone normalidad; las operaciones tienen colas gruesas |
| C-09 | **MaxDD p95 por bootstrap por bloques de un mes natural**, 10,000 trayectorias de la misma duración que el periodo, con el riesgo por operación de la regla y capital compuesto | Conserva las rachas de pérdidas, que son las que crean el drawdown |
| C-10 | **PBO por CSCV con 16 particiones sobre la rejilla de robustez completa** ({−20%, 0, +20%} en cada parámetro). *Cambio respecto a la v0:* como no hay rejilla de selección (C-04), el PBO se calcula sobre la vecindad de parámetros | Mide si el resultado depende de un punto concreto de parámetros |
| C-11 | **N del DSR = número de especificaciones principales evaluadas en todas las hipótesis** (filas de `trials.csv` con `tipo_muestra = principal`, incluidas versiones posteriores como H1-v2). Las variantes de robustez y de PBO se anotan con `tipo_muestra = robustez` y no cuentan. *Cambio respecto a la v0:* contar las variantes de robustez inflaría N sin que haya búsqueda | El DSR corrige por búsqueda múltiple; las variantes de robustez no son búsqueda |
| C-12 | **El backtest usa el mismo motor de riesgo** (`src/trading/risk/`, límites F7-F8) | Lo que se valida es lo que se va a operar |
| C-13 | **Se aceptan los supuestos de la sección 3** | Conservadores |
| C-14 | **Costes:** comisión taker 0.05% por lado en entrada y salida (sin suponer maker ni descuento BNB). Slippage por lado: BTC/ETH 0.05%, alts 0.10%; en stops, el doble (0.10% y 0.20%). Funding histórico real | Conservador para órdenes de USD 100-3,000; el gate añade el stress ×1.5 |
| C-15 | **Las 200 operaciones se cuentan en el total de la hipótesis** (activos y direcciones) | Junto con C-16 |
| C-16 | **Cortos habilitados solo si** el gate completo pasa sobre el total **y** cada dirección por separado tiene esperanza neta > 0 | Exigir el gate completo por dirección requeriría ≥200 operaciones por lado |
| C-17 | **Concentración mensual:** beneficio neto del mes / beneficio neto total fuera de muestra, en R, meses naturales en UTC; ningún mes > 30% | Literal del plan |
| C-18 | **Entrada en la apertura siguiente** (regla principal). **Sensibilidad declarada** (informativa, no forma parte del gate): en estrategias de 4h, las señales de las velas que cierran a las 08:00 y 12:00 UTC (02:00 y 06:00 en CDMX) entran en la apertura de las 16:00 UTC | Mide el coste de que el propietario apruebe de día en nivel B |
| C-19 | *(nueva en v1)* **Nocional mínimo:** si el tamaño por riesgo queda por debajo del mínimo, no se opera. Supuesto conservador hasta la F1: 100 USDT en BTC y ETH, 20 USDT en alts | Con USD 1,500 y riesgo de USD 7.50, los stops anchos dan órdenes pequeñas; el backtest no puede asumir órdenes que el exchange rechazaría |
| C-20 | *(nueva en v1)* **Apalancamiento configurado en el exchange: 3×, margen aislado** | Con 3× la liquidación queda a ≈33%: cualquier stop ≤ ≈11% cumple la regla de 3× la distancia al stop |

## 5. Registro en `trials.csv`

- `tipo_muestra`: `principal` (la especificación pre-registrada), `robustez` (±20% y rejilla del PBO), `costes_x1.5`, `sensibilidad` (C-18), `holdout` (una sola vez, en el gate).
- `prereg_commit`: hash del commit de fusión de este protocolo y del pre-registro de la hipótesis.

## 6. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador con 18 decisiones abiertas |
| v1 | 2026-10-23 | Decisiones tomadas por delegación del propietario; hechos verificados del archivo de Binance; nuevas C-19 (nocional mínimo) y C-20 (apalancamiento del exchange); C-10 y C-11 ajustadas a C-04 |
