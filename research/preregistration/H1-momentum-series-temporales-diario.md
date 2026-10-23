# Pre-registro H1-v1: momentum de series temporales diario en BTC

- **ID:** H1 · **Versión:** v1 · **Prioridad:** Alta (plan §5)
- **Estado:** FUSIONADO en `main` el 23-oct-2026 (PR #1)
- **Fecha:** 2026-10-23 · **Autor:** Claude, con decisiones delegadas por el propietario el 23-oct-2026 · **Aprobado por:** propietario, 23-oct-2026
- **Commit de fusión:** `4614d659247e57ef6f01614b4986c125fe5468f9`
- **Protocolo común:** `00-protocolo-comun.md` v1

## 1. Hipótesis

- **Enunciado [hipótesis]:** en BTC, el signo de la rentabilidad de la última semana predice el signo de la rentabilidad de los días siguientes; una estrategia que se posiciona cada día en la dirección de esa rentabilidad tiene esperanza neta positiva después de comisiones de futuros, funding y slippage.
- **H0:** esperanza neta por operación ≤ 0 R. **Alternativa:** > 0 R.
- **Base:** Liu y Tsyvinski, "Risks and Returns of Cryptocurrency", *Review of Financial Studies* 34(6), 2021: documentan momentum de series temporales significativo a frecuencia diaria y semanal, con la rentabilidad de la última semana prediciendo las semanas siguientes. **[por verificar]**: el texto del paper no se pudo descargar desde este entorno (red bloqueada); la ventana de 7 días se basa en los resúmenes publicados del paper.

## 2. Datos

- Velas diarias (cierre 00:00 UTC) y funding del perpetuo BTCUSDT (C-01).
- Periodo de investigación: 2020-01-01 → 2024-12-31 (C-03). Holdout sellado: 2025-01-01 → fecha del gate.

## 3. Universo

- **Solo BTC** (decisión H1-05). ETH queda fuera de esta versión por dos motivos:
  1. BTC y ETH son una sola exposición (plan §3): ambos a la vez obligarían a repartir el riesgo (0.25% cada uno).
  2. Con 0.25% de riesgo (USD 3.75) y un stop diario típico de 5-8%, la orden de BTC quedaría en USD 45-75, por debajo del nocional mínimo de ≈100 USDT (C-19): la estrategia no se podría ejecutar.
- Una versión con ETH sería un pre-registro nuevo y contaría como otra especificación en el DSR.

## 4. Regla exacta

Notación: `C_t` = cierre diario de la vela que termina en `t` (00:00 UTC); `ATR14_t` = ATR de Wilder de 14 días calculado con velas hasta `t` inclusive.

```
señal_t = +1 si C_t / C_{t-7} - 1 > 0
          -1 si C_t / C_{t-7} - 1 < 0
          señal_{t-1} si es exactamente 0

en cada cierre diario t (desde que hay 14 días de ATR y 7 de rentabilidad):
    si hay posición y su dirección es contraria a señal_t:
        cerrar en la apertura de t+1                                  # salida por cambio de señal
    si no hay posición (o se acaba de cerrar) y la entrada está permitida:
        ENTER en la dirección de señal_t en la apertura de t+1
        stop fijo = entrada - 2 × ATR14_t (largo) | entrada + 2 × ATR14_t (corto)
    la posición también se cierra si se alcanza el stop (sección 3 del protocolo)

entrada permitida:
    tras un cierre por cambio de señal: sí (se invierte la posición)
    tras un stop: solo cuando la señal cambie de signo; la nueva entrada es en la dirección nueva
tamaño: motor de riesgo, 0.5% del capital; si queda por debajo del nocional mínimo, no se opera
```

- **4.2 Dirección:** largo y corto. Los cortos solo se habilitan si se cumple C-16.
- **4.3 Stop:** fijo desde la entrada, sin trailing (H1-04).
- **4.4 Salida:** cambio de signo de la señal o stop. Sin salida por tiempo (H1-06).

## 5. Parámetros

| Parámetro | Valor pre-registrado | Variantes ±20% (robustez y PBO) |
|---|---|---|
| L: ventana de la rentabilidad (días) | 7 | 6, 8 |
| n: ventana del ATR (días) | 14 | 11, 17 |
| k: múltiplo de ATR del stop | 2 | 1.6, 2.4 |

- Especificaciones principales: **1** (C-04). Rejilla de robustez completa para el PBO: 3³ = 27 variantes.
- **Estimación previa del número de operaciones (sin datos):** para un paseo aleatorio, el signo de una suma móvil de 7 días cambia con una frecuencia de arccos(6/7)/π ≈ 0.17 por día, es decir ≈60 cambios al año. En 5 años son ≈290 operaciones menos el efecto de los stops y de las órdenes no ejecutables. Es una estimación teórica, no un resultado: si el backtest da menos de 200 operaciones, H1 no pasa el gate.

## 6. Costes asumidos

Los del protocolo común (C-14): comisión taker 0.05% por lado, slippage 0.05% por lado (0.10% en stops), funding histórico real; stress ×1.5 en el gate.

## 7. Protocolo de validación

Parámetros fijados a priori (C-04); todo el periodo posterior al calentamiento es fuera de muestra. PBO sobre la rejilla de 27 variantes (C-10); DSR con N de C-11.

## 8. Métricas y gate de la F4

Gate del plan §5 sin cambios, con las definiciones del protocolo común v1.

## 9. Criterios de invalidación

- Cualquier resultado sobre datos ≥2025-01-01 antes del gate.
- Ejecutar una variante fuera de la rejilla pre-registrada, o cualquier ejecución sin anotarla en `trials.csv`.
- Cambiar la regla después de ver resultados (requiere H1-v2 y cuenta como especificación adicional en el DSR).

## 10. Decisiones

| ID | Decisión | Justificación |
|---|---|---|
| H1-01 | (a) Signo de la rentabilidad acumulada de L días; siempre largo o corto | Definición estándar de momentum de series temporales |
| H1-02 | L = 7 días, valor único | La referencia sitúa el efecto en la rentabilidad de la última semana |
| H1-03 | (a) Evaluación diaria al cierre de 00:00 UTC | El plan la define como "diaria"; con evaluación semanal habría ≈130 operaciones en 5 años, por debajo del gate |
| H1-04 | (a) Stop fijo a 2 × ATR(14) desde la entrada | Sin una segunda regla de salida; k = 2 mantiene la orden por encima del nocional mínimo en la mayoría de los días |
| H1-05 | (a) Solo BTC | Ver sección 3 (exposición conjunta y nocional mínimo) |
| H1-06 | (a) Sin salida por tiempo | La salida natural es el cambio de señal |
| H1-07 | (a) Tras un stop, reentrada solo con cambio de señal | No reentrar en la misma tendencia que acaba de fallar |

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador con decisiones abiertas |
| v1 | 2026-10-23 | Decisiones tomadas por delegación del propietario; universo reducido a BTC |
