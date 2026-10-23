# Pre-registro H2-v1: ruptura de canal en 4h con filtro de volatilidad

- **ID:** H2 · **Versión:** v1 · **Prioridad:** Alta (plan §5)
- **Estado:** FUSIONADO en `main` el 23-oct-2026 (PR #1)
- **Fecha:** 2026-10-23 · **Autor:** Claude, con decisiones delegadas por el propietario el 23-oct-2026 · **Aprobado por:** propietario, 23-oct-2026
- **Commit de fusión:** `4614d659247e57ef6f01614b4986c125fe5468f9`
- **Protocolo común:** `00-protocolo-comun.md` v1

## 1. Hipótesis

- **Enunciado [hipótesis]:** cuando el precio cierra fuera de su rango de los últimos 10 días en velas de 4h **y la volatilidad de corto plazo está por encima de la de largo plazo**, el movimiento continúa lo suficiente como para dejar esperanza neta positiva después de costes, en ambas direcciones.
- **H0:** esperanza neta por operación ≤ 0 R. **Alternativa:** > 0 R.
- **Base:** familia de reglas de ruptura de canal (tipo Donchian) de seguimiento de tendencia. El filtro descarta rupturas en volatilidad decreciente, que suelen ser derivas sin impulso. No hay una referencia académica para esta variante concreta.

## 2. Datos

- Velas de 4h (límites en 00, 04, 08, 12, 16 y 20 UTC), velas diarias (para el universo) y funding de los perpetuos con margen en USDT (C-01).
- Periodo de investigación: 2020-01-01 → 2024-12-31 (C-03). Holdout sellado: 2025-01-01 → fecha del gate.
- **[por verificar en F3]** Que el archivo de Binance conserva los contratos deslistados; si no, el universo tiene sesgo de supervivencia y hay que declararlo antes de ejecutar.

## 3. Universo (H2-06)

- **BTC, ETH y las 8 alts más líquidas**, reconstituido el día 1 de cada mes a las 00:00 UTC:
  - candidatas: perpetuos con margen en USDT con al menos 90 días de histórico en esa fecha;
  - excluidos: BTC y ETH (ya incluidos), activos base que sean stablecoins, contratos de índices y activos tokenizados;
  - orden: mediana del volumen diario en USDT de los 30 días anteriores; entran las 8 primeras.
- Una posición abierta sigue su curso aunque el activo salga del universo; no se abren posiciones nuevas en activos fuera del universo.
- BTC y ETH son una sola exposición (plan §3); no se crean otros grupos de correlación (H2-08).

## 4. Regla exacta

Notación por activo: `H_t`, `L_t`, `C_t` = máximo, mínimo y cierre de la vela de 4h que termina en `t`; `ATR14_t` y `ATR100_t` = ATR de Wilder de 14 y 100 velas hasta `t` inclusive.

```
canal_alto_t  = max(H_{t-60} … H_{t-1})        # 60 velas = 10 días, sin la vela t
canal_bajo_t  = min(L_{t-60} … L_{t-1})
salida_alta_t = max(H_{t-20} … H_{t-1})        # 20 velas ≈ 3.3 días
salida_baja_t = min(L_{t-20} … L_{t-1})
filtro_t      = ATR14_t > ATR100_t

ruptura_larga_t = C_t > canal_alto_t  y  C_{t-1} <= canal_alto_{t-1}     # nueva ruptura
ruptura_corta_t = C_t < canal_bajo_t  y  C_{t-1} >= canal_bajo_{t-1}

al cierre de cada vela t, para cada activo del universo sin posición:
    si ruptura_larga_t y filtro_t -> ENTER_LONG en la apertura de t+1, stop = entrada - 2 × ATR14_t
    si ruptura_corta_t y filtro_t -> ENTER_SHORT en la apertura de t+1, stop = entrada + 2 × ATR14_t
con posición larga: salir en la apertura de t+1 si C_t < salida_baja_t, o en el stop
con posición corta: salir en la apertura de t+1 si C_t > salida_alta_t, o en el stop
tamaño: motor de riesgo, 0.5% del capital; si queda por debajo del nocional mínimo, no se opera
```

- La condición de "nueva ruptura" exige que la vela anterior no estuviera ya fuera del canal: tras una salida o un stop, solo se vuelve a entrar con una ruptura nueva (H2-05).
- **[fijado, ADR-004]** Solo velas cerradas; sin órdenes de entrada intra-vela.
- **4.2 Dirección:** largo y corto; cortos sujetos a C-16.
- **4.5 Posiciones simultáneas (H2-07):** máximo 1 por activo; el resto lo limita el motor de riesgo (apalancamiento ≤2×, pérdida diaria/semanal, BTC+ETH como una exposición). Las señales vetadas se registran con el motivo y no cuentan como operaciones.

## 5. Parámetros

| Parámetro | Valor pre-registrado | Variantes ±20% |
|---|---|---|
| N: velas del canal de entrada | 60 | 48, 72 |
| M: velas del canal de salida | 20 | 16, 24 |
| ATR corto (velas) | 14 | 11, 17 |
| ATR largo (velas) | 100 | 80, 120 |
| k: múltiplo de ATR del stop | 2 | 1.6, 2.4 |

- Especificaciones principales: **1** (C-04). Rejilla de robustez completa para el PBO: 3⁵ = 243 variantes.
- El universo (8 alts, 30 días, 90 días de historia) no forma parte de la prueba ±20%: es una definición, no un parámetro de la regla.

## 6. Costes asumidos

Los del protocolo común (C-14): comisión taker 0.05% por lado; slippage por lado 0.05% en BTC/ETH y 0.10% en alts, el doble en stops; funding histórico real; stress ×1.5 en el gate.

## 7. Protocolo de validación

Parámetros fijados a priori (C-04). PBO sobre la rejilla de 243 variantes (C-10); DSR con N de C-11. Sensibilidad informativa de entrada diurna (C-18).

## 8. Métricas y gate de la F4

Gate del plan §5 sin cambios, con las definiciones del protocolo común v1.

## 9. Criterios de invalidación

Los mismos que H1, más: construir el universo con información posterior a la fecha de reconstitución.

## 10. Decisiones

| ID | Decisión | Justificación |
|---|---|---|
| H2-01 | (c) Un único N = 60 velas (10 días) | Sin rejilla de selección (C-04) |
| H2-02 | **(b) Expansión: ATR(14) > ATR(100)** en la vela de señal | Hipótesis con la lectura económica más directa (las rupturas con volatilidad creciente son impulso; las de volatilidad decreciente, deriva) y que conserva muestra; la compresión (a) es una hipótesis distinta y, si se quiere probar, va en otro pre-registro |
| H2-03 | (a) Stop fijo a 2 × ATR(14) desde la entrada | Distancia estable; con ATR de 4h la orden queda por encima del nocional mínimo |
| H2-04 | (a) Salida por el canal opuesto de 20 velas, sin objetivo fijo | Coherente con una hipótesis de continuación |
| H2-05 | (a) Reentrada solo con una ruptura nueva | Implementado con la condición de "nueva ruptura" |
| H2-06 | **(b) BTC, ETH y las 8 alts más líquidas** (*cambio respecto a la recomendación de la v0*) | Con solo BTC y ETH, una ruptura de 10 días con filtro generaría del orden de 15-20 operaciones al año en total (estimación teórica): unas 80-100 en 5 años, muy por debajo de 200. El plan contempla "pocas alts líquidas" |
| H2-07 | (a) Lo que permita el motor de riesgo, máximo 1 por activo | Un único conjunto de límites |
| H2-08 | (a) Solo el grupo BTC+ETH del plan | Ampliar grupos es cambiar límites de riesgo (ADR) |

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador con decisiones abiertas |
| v1 | 2026-10-23 | Decisiones tomadas por delegación del propietario; universo ampliado a 8 alts líquidas; regla de "nueva ruptura" explícita |
