# Protocolo común de investigación (F4)

- **Versión:** v0 · **Estado:** BORRADOR (decisiones abiertas C-01 a C-18)
- **Fecha:** 2026-10-23 · **Aplica a:** H1, H2, H3, H4
- **Fuentes:** plan maestro v2 §3, §5; CLAUDE.md reglas 6 y 7; ADR-001, ADR-004

Este documento fija lo que comparten todas las hipótesis para no repetirlo ni dejar que cada una lo resuelva a su manera.
Lo que el plan ya decide se marca **[fijado]**; lo demás es una decisión abierta del propietario.

## 1. Lo que ya está fijado

- **[fijado]** Comisiones de futuros y funding incluidos en **todos** los backtests (plan §5).
- **[fijado]** Holdout sellado: 2025-01-01 → fecha del gate. Se abre una sola vez, en el gate de la F4, con aprobación explícita (CLAUDE.md regla 7). El periodo de investigación termina el 2024-12-31.
- **[fijado]** Señales solo sobre velas cerradas de 4h o 1d con límites en UTC; entrada después del cierre de la vela de señal (ADR-004).
- **[fijado]** Toda variante ejecutada se anota en `research/trials.csv` (CLAUDE.md regla 6).
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

## 2. Supuestos de ejecución en el backtest

Estos supuestos no son reglas de estrategia, pero cambian los resultados; se pre-registran igual.

| Elemento | Propuesta | Estado |
|---|---|---|
| Precio de entrada | Apertura de la vela siguiente a la de señal, con orden a mercado (taker) más slippage | Ver C-13 |
| Stop alcanzado dentro de la vela | Se ejecuta al precio del stop más slippage; si la vela abre más allá del stop (gap), al precio de apertura más slippage | Ver C-13 |
| Stop y otra salida en la misma vela | Se asume que el stop se ejecuta primero (supuesto conservador) | Ver C-13 |
| Funding | Se aplica la tasa histórica real en cada liquidación mientras la posición está abierta, según el intervalo de liquidación que tuviera el contrato en esa fecha | **[fijado]** por plan §5; fuente por verificar en F3 |

## 3. Decisiones abiertas comunes

| ID | Pregunta | Opciones | Recomendación (no es decisión) | Decisión del propietario |
|---|---|---|---|---|
| C-01 | ¿Qué contratos se usan en el backtest y cuáles en operación? El capital está en USDC (plan §1). | (a) Backtest con perpetuos con margen en USDT (histórico desde 2019) y operación en el contrato que confirme la F1, tratando la diferencia como coste. (b) Backtest y operación solo con contratos con margen en USDC (histórico más corto, por verificar). | (a): el histórico en USDC probablemente no da muestra suficiente; por verificar en F1/F3 | |
| C-02 | ¿Los largos se ejecutan en spot o en perpetuos? | (a) Ambas direcciones en perpetuos (costes y funding homogéneos). (b) Largos en spot, cortos en perpetuos. | (a): una sola estructura de costes y un solo instrumento por activo | |
| C-03 | ¿Desde qué fecha empieza el periodo de investigación? | (a) Desde el listado del perpetuo de cada activo (BTC ≈ sep-2019, por verificar). (b) Desde 2017 con datos spot para la señal y costes de perpetuo simulados donde no haya histórico. | (a): no inventa funding para años sin perpetuo | |
| C-04 | ¿Esquema de walk-forward? | (a) Parámetros fijados a priori, sin optimización: todo el periodo cuenta como fuera de muestra. (b) Anclado: entrenamiento creciente desde el inicio, prueba de 6 meses, paso de 6 meses. (c) Rodante: entrenamiento de 2 años, prueba de 6 meses, paso de 6 meses. | (b) si hay rejilla de parámetros; (a) si la hipótesis se pre-registra con un único valor | |
| C-05 | ¿Cómo se definen los 3 regímenes del gate? | (a) Tendencia de BTC: alcista si el cierre diario está por encima de su media de 200 días y la media sube; bajista si está por debajo y baja; lateral el resto. (b) Periodos de calendario fijados ahora. (c) Terciles de volatilidad realizada de BTC a 30 días. | (a): definición objetiva y calculable sin mirar resultados | |
| C-06 | ¿Qué significa "sigue rentable" con costes ×1.5 y parámetros ±20%? | (a) Esperanza neta > 0 (estimación puntual). (b) Límite inferior del IC90% > 0. (c) PF neto ≥1.25. (d) PF neto > 1. | (a) para parámetros ±20% y (b) para costes ×1.5; es la combinación más exigente que sigue siendo alcanzable | |
| C-07 | ¿En qué unidad se mide la esperanza? | (a) Múltiplos de R netos de costes (R = riesgo planificado de la operación). (b) % de rentabilidad por operación. | (a): coincide con el tamaño por riesgo del motor | |
| C-08 | ¿Cómo se calcula el IC90% de la esperanza? | (a) Bootstrap percentil, 10,000 remuestreos, bilateral (límite inferior = percentil 5). (b) Intervalo t de Student. | (a): no supone normalidad, y las operaciones tienen colas gruesas | |
| C-09 | ¿Cómo se simula el MaxDD p95 de Monte Carlo? | (a) Bootstrap iid de las operaciones fuera de muestra, 10,000 trayectorias, con riesgo fijo de 0.5% por operación. (b) Bootstrap por bloques de un mes para conservar rachas. | (b): las rachas de pérdidas importan para el drawdown | |
| C-10 | ¿Cómo se calcula el PBO? | (a) CSCV con 16 particiones sobre todas las variantes de la rejilla pre-registrada. (b) CSCV con 10 particiones. | (a), siempre que haya variantes suficientes; con un único valor de parámetros el PBO no aplica y hay que decir cómo se trata | |
| C-11 | ¿Qué número de pruebas usa el DSR? | (a) Filas de `trials.csv` de la hipótesis. (b) Filas de todas las hipótesis. | (b): es la corrección más conservadora frente a búsqueda múltiple | |
| C-12 | ¿El backtest aplica el motor de riesgo (tamaño por riesgo, apalancamiento ≤2×, BTC+ETH como una exposición, pérdidas diaria/semanal)? | (a) Sí, el mismo código del motor. (b) No; se evalúan las señales en bruto y el motor se aplica desde la F6. | (a): lo que se valida es lo que se va a operar | |
| C-13 | ¿Se aceptan los supuestos de ejecución de la sección 2? | (a) Sí. (b) Cambios (indicar). | (a) | |
| C-14 | ¿Valores de costes? | Comisión: taker en ambos lados, sin suponer maker, al valor estándar de la cuenta verificado en F1 (valor de referencia por verificar: 0.05% por lado). Slippage por lado: BTC/ETH 0.02% / 0.05% / otro; alts 0.10% / 0.20% / otro. Stops: el doble del slippage de entrada / igual / otro. | BTC/ETH 0.05%, alts 0.20%, stops ×2: conservador para tamaños de USD 375-3,000 | |
| C-15 | ¿El mínimo de 200 operaciones se cuenta sumando activos y direcciones? | (a) Sí, total de la hipótesis. (b) Por activo. (c) Por dirección. | (a), combinado con C-16 | |
| C-16 | ¿Qué exige "validada en ambas direcciones" para habilitar cortos? | (a) El gate completo se evalúa sobre el total y, además, cada dirección por separado tiene esperanza neta > 0. (b) Cada dirección pasa el gate completo por separado. (c) Basta con el gate sobre el total. | (a): (b) exige ≥200 operaciones por dirección, difícil con este universo; (c) no protege contra una dirección perdedora | |
| C-17 | ¿Cómo se calcula "ningún mes aporta más del 30% del beneficio"? | (a) Beneficio neto del mes / beneficio neto total fuera de muestra, en R, meses naturales en UTC. (b) Otro. | (a) | |
| C-18 | ¿Se fija una ventana de validez de la señal en el backtest para reflejar la aprobación manual del nivel B (ADR-004, ADR-006)? | (a) No; se entra en la apertura siguiente. (b) Sí: la entrada se retrasa N horas (por ejemplo, la siguiente vela en horario diurno de México) y se mide el efecto. | (a) en el pre-registro y (b) como análisis de sensibilidad declarado aquí | |

## 4. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador inicial |
