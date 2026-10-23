# Aclaraciones de implementación del pre-registro v1

- **Aplica a:** protocolo común v1, H1-v1, H2-v1 y H4-v1 (fusionados en `4614d65`).
- **Fecha:** 2026-10-23 · **Autor:** Claude, con la delegación del propietario del 23-oct-2026 y su confirmación del mismo día de que `4614d65` está congelado.
- **Momento:** este documento se escribe y se versiona **antes** de descargar datos de mercado y antes de cualquier backtest. Ningún punto se decidió mirando resultados.
- **Qué es y qué no es:** traduce a reglas exactas lo que el pre-registro dejaba sin concretar (auditoría `docs/auditoria/2026-10-23-auditoria.md`, hallazgos A-03 y A-04). **No cambia** ninguna regla, parámetro, umbral ni coste. Cada corrida en `research/trials.csv` anota el hash del pre-registro **y** el de este documento.

## 1. Datos

1. Fuente: archivo público de Binance (`data.binance.vision`, leído por su espejo `s3-ap-northeast-1.amazonaws.com/data.binance.vision`). Cada fichero se verifica con su `.CHECKSUM` SHA-256; un fichero que no cuadra no se usa.
2. Velas identificadas por su hora de apertura (UTC); una vela de intervalo `I` abierta en `t` cierra en `t + I`.
3. **Periodo de investigación:** velas con apertura ≥ 2020-01-01 00:00 UTC y cierre ≤ 2025-01-01 00:00 UTC. Los indicadores se calientan solo con datos del periodo, salvo las etiquetas de régimen (punto 6).
4. Funding: ficheros `fundingRate` (`calc_time`, `funding_interval_hours`, `last_funding_rate`).
5. Formatos: las velas spot no tienen cabecera y las de futuros recientes sí; las marcas de tiempo en microsegundos (spot desde 2025) se normalizan a milisegundos.
6. **Regímenes (C-05):** cierres diarios del par **spot** BTCUSDT desde 2019-01-01 (solo para etiquetar). Media simple de 200 días y pendiente = media(t) − media(t − 20 días).

## 2. Universo de H2

1. **Candidatos:** símbolos del archivo de perpetuos USDⓈ-M que terminan en `USDT` y no contienen `_` (los que llevan `_` son futuros con vencimiento). Activo base = símbolo sin el sufijo `USDT`.
2. **Exclusiones por activo base exacto** (la trampa: `TUSDT` y `BUSDT` son los tokens T y B, no stablecoins):
   - Stablecoins y divisas: USDC, BUSD, TUSD, FDUSD, USDP, DAI, USDE, PYUSD, EUR, AEUR, USTC, USD1, RLUSD, USDBRL.
   - Índices: BTCDOM, DEFI, FOOTBALL, BLUEBIRD.
   - Activos tokenizados (acciones y metales): AAPL, AMZN, COIN, CRCL, GOOGL, HOOD, META, MSFT, MSTR, NVDA, QQQ, SPY, TSLA, PAXG, XAUT, XAU, XAG.
   - Envoltorios de BTC o ETH: WBTC, WETH, WBETH, BETH, STETH, WSTETH, CBETH.
3. **Elegibilidad en la fecha de reconstitución `D`** (día 1 de cada mes, 00:00 UTC): la primera vela diaria del símbolo abrió como mínimo 90 días antes de `D`, y el símbolo tiene vela diaria del día `D − 1` (sigue cotizando).
4. **Orden:** mediana del `quote_volume` (USDT) de las velas diarias de los 30 días anteriores a `D` (días `D−30 … D−1` con datos). Empates por orden alfabético del símbolo.
5. BTCUSDT y ETHUSDT forman parte del universo siempre que cumplan el punto 3.
6. **Deslistados:** el archivo los conserva (verificado: LUNAUSDT hasta 2022-05, ANCUSDT, TOMOUSDT). Si un símbolo deja de tener velas con una posición abierta, la posición se cierra al último cierre disponible con motivo `DESLISTADO`.

## 3. Indicadores y señales

1. **ATR:** media de Wilder del rango verdadero, con semilla igual a la media simple de los primeros `n` rangos verdaderos. El rango verdadero usa el cierre anterior.
2. **H1:** la primera posición se abre en la primera evaluación con señal definida (7 rentabilidades y ATR(14) disponibles). Señal 0 sin señal previa = sin posición.
3. **Redondeo de las variantes ±20%** de parámetros enteros: al entero más cercano, con medio hacia arriba (por ejemplo, 7 × 0.8 = 5.6 → 6). Coincide con las tablas de los pre-registros.

## 4. Ejecución simulada y costes

1. **Precios con slippage (C-14):** la entrada a mercado se ejecuta a `apertura × (1 + s)` en largos y `apertura × (1 − s)` en cortos. Las salidas por regla y por fin de periodo aplican `s` en contra; los stops aplican `2s` en contra sobre el precio del stop, o sobre la apertura si hubo gap. `s` = 0.05% en BTC/ETH y 0.10% en alts.
2. **Comisión:** taker 0.05% del nocional ejecutado, en la entrada y en la salida.
3. **Funding:** se cobra o se paga en cada `calc_time` con `entrada < calc_time ≤ salida`. El nocional se valora con el cierre de la vela de 4h que cierra en o antes de `calc_time`. Los largos pagan si la tasa es positiva y los cortos si es negativa.
4. **Fin del periodo:** las posiciones abiertas se cierran al último cierre anterior a 2025-01-01, con motivo `FIN_DE_PERIODO`, y cuentan como operaciones.
5. **Motor de riesgo (C-12):** se usa el motor real con los **límites firmados de F7-F8** (`limits_f7_f8.toml`):
   - Capital inicial USD 1,500, compuesto.
   - Capital a mercado al cierre de cada vela; inicio de día y de semana a las 00:00 UTC (lunes para la semana).
   - Apalancamiento del exchange 3× aislado (C-20).
   - Margen de mantenimiento **estimado**: 0.4% en BTC y ETH, 2.5% en alts, sin importe de mantenimiento.
   - Nocional mínimo (C-19): 100 USDT en BTC y ETH, 20 USDT en alts.
   - Sin paso de cantidad.
   - Las señales vetadas se registran con su motivo y no son operaciones.
6. Las reglas **propuestas** del motor v1 (ADR-013) no forman parte de la corrida principal. Se ejecutan aparte como sensibilidad informativa (`tipo_muestra = sensibilidad`) y no cuentan en el DSR.

## 5. Métricas del gate

1. **R de una operación** = P&L neto / riesgo planificado, calculado por el motor al entrar e incluyendo los costes.
2. **IC90% de la esperanza (C-08):** bootstrap percentil iid sobre las operaciones, 10,000 remuestreos, semilla 20261023. El remuestreo por bloques mensuales solo se usa para el Monte Carlo del drawdown (C-09).
3. **MaxDD p95 (C-09):** se agrupan las operaciones por mes de salida y se remuestrean meses con reemplazo hasta el número de meses del periodo, 10,000 trayectorias, semilla 20261023. El capital evoluciona como `capital × (1 + 0.005 × R)`.
4. **DSR (C-11):**
   - SR = media(R) / desviación(R) por operación, sin anualizar; T = número de operaciones; asimetría γ₃ y curtosis γ₄ de R.
   - N = filas `principal` de `trials.csv` en el momento del gate.
   - SR₀ = √V · ((1 − γ) Φ⁻¹(1 − 1/N) + γ Φ⁻¹(1 − 1/(N·e))), con γ = 0.5772 (constante de Euler-Mascheroni) y V = varianza de los SR de las pruebas principales. Si N = 1, SR₀ = 0.
   - DSR = Φ((SR − SR₀) √(T − 1) / √(1 − γ₃·SR + (γ₄ − 1)/4 · SR²)).
5. **PBO (C-10):**
   - Matriz de meses naturales (filas, de 2020-01 a 2024-12) por variantes de la rejilla completa ±20% (columnas), con la suma de R del mes.
   - Los 60 meses se reparten en 16 bloques contiguos lo más iguales posible (12 bloques de 4 meses y 4 de 3).
   - Métrica: media/desviación de los meses.
   - Se recorren las C(16,8) = 12,870 combinaciones. PBO = fracción en que la mejor variante dentro de muestra queda por debajo de la mediana fuera de muestra (logit ≤ 0).
6. **Regímenes (C-05):** cada operación toma la etiqueta del día de entrada.
7. **Concentración (C-17):** se suman las R por mes de salida. Si el total es ≤ 0, el criterio falla.
8. **H4, filtros aleatorios (H4-06):**
   - `k` = entradas de la base que el filtro habría bloqueado.
   - Cada filtro aleatorio quita `k` operaciones al azar de la lista de operaciones de la base y calcula la esperanza del resto; 10,000 repeticiones, semilla 20261023.
   - La comparación usa el percentil 90.

## 6. Detalles de implementación (v1.1)

Escritos antes de descargar el dataset y antes de cualquier backtest; hasta aquí solo se inspeccionó el formato de 5 ficheros de muestra (cabecera y 3 filas de cada uno). Tampoco cambian reglas, parámetros, umbrales ni costes: fijan cómo se implementan los puntos anteriores.

1. **Rango verdadero de la primera vela:** la primera vela de cada serie no tiene cierre anterior y no produce rango verdadero. El primero sale de la segunda vela, y ATR(n) existe desde la vela n + 1 (semilla: media simple de los n primeros rangos).
2. **Universo vigente:** en cada instante `t` rige el universo de la última reconstitución `D ≤ t`. La vela de 4h que cierra justo en `D` ya usa el universo nuevo (que solo mira datos hasta `D − 1`).
3. **Varias señales en la misma vela:**
   - Primero se ejecutan las salidas y después las entradas.
   - Las entradas se presentan al motor de riesgo en el orden del universo (mediana de `quote_volume`, de mayor a menor) y cada aprobada cuenta para la siguiente.
   - En H1 (un solo activo) la salida por cambio de señal y la nueva entrada ocurren en la misma apertura.
4. **Tamaño y riesgo planificado:**
   - En la apertura de `t + 1` el precio de ejecución es `P = apertura × (1 ± s)` y el stop es `P ∓ k × ATR_t`.
   - El tamaño lo da `size_by_risk` con el capital a mercado al cierre de `t`, el 0.5% de riesgo y `CostModel(comisión = 0.05%, slippage = s)`. El motor evalúa la propuesta con el mismo modelo de costes.
   - El riesgo planificado (denominador de R) es `trade_risk` del motor con ese modelo. Como `P` ya incluye el slippage de entrada, el motor lo cuenta dos veces: sobreestima un poco el riesgo, lo que es conservador.
   - El tope de nocional de `size_by_risk` es el apalancamiento que queda libre (2× del capital menos el nocional abierto).
5. **Stops:**
   - Se comprueban desde la vela de entrada inclusive.
   - Largo: si `apertura ≤ stop`, la salida es `apertura × (1 − 2s)`; si no, y `mínimo ≤ stop`, la salida es `stop × (1 − 2s)`. Corto: simétrico.
6. **Riesgo de las posiciones abiertas** (`OpenPosition.risk_to_stop`): pérdida adicional, con la comisión y el slippage de stop (2s), si saltara el stop desde el cierre actual; 0 si el stop protege beneficio.
7. **Paradas del motor en el backtest:**
   - El drawdown se mide sobre el capital a mercado al cierre de cada vela.
   - Si salta el corte duro (20%), se cierran todas las posiciones en la apertura siguiente y no se abren más en toda la corrida (no hay propietario que lo rearme).
   - La parada del 15% bloquea entradas mientras dure.
8. **Funding y holdout:**
   - El funding con `calc_time ≥ 2025-01-01 00:00 UTC` pertenece al holdout y no se lee.
   - Una posición cerrada por `FIN_DE_PERIODO` no paga la liquidación de las 00:00 del 1-ene-2025.
   - Las salidas por fin de periodo usan el cierre de la última vela (que cierra a las 00:00 del 1-ene-2025) con slippage `s`.
9. **H4, "liquidadas antes del cierre de t":** `calc_time < t`, estrictamente.
10. **Deslistados:** el cierre por `DESLISTADO` aplica slippage `s` y comisión, como una salida por regla.
11. **Descarga:** solo se descargan los meses hasta 2024-12 inclusive; los ficheros del holdout no se descargan en la F3.

## 7. Detalles de implementación (v1.2)

Escritos después de descargar y validar el dataset `48f73c7…` y **antes de ejecutar cualquier backtest sobre datos reales** (solo se han corrido pruebas con datos sintéticos). No cambian reglas, parámetros, umbrales ni costes.

1. **Hora del funding:** el archivo registra cada liquidación con 0-47 ms de retraso sobre la hora en punto. `calc_time` se redondea hacia abajo al minuto.
2. **Funding en la vela del stop:** el stop se supone al final de la vela en que salta, así que se cobran las liquidaciones estrictamente dentro de esa vela.
3. **Costes ×1.5:**
   - Se multiplican por 1.5 la comisión, el slippage (entradas, salidas y stops) y el funding **pagado**; el funding cobrado no cambia.
   - El motor dimensiona con los costes multiplicados.
4. **PF** = suma de R positivos / |suma de R negativos|.
5. **Ambas direcciones (C-02):**
   - El backtest usa los límites firmados de F7-F8 con `short_enabled_strategies = {hipótesis}`, porque sin eso no se podrían evaluar los cortos que exige C-16.
   - Los límites firmados no cambian; habilitar cortos de verdad sigue C-16 y un ADR.
6. **H4 con poco historial:** con menos de `count` liquidaciones previas, el filtro no actúa.
7. **Rejilla de H4 para el PBO:**
   - Umbral {0.04, 0.05, 0.06}% × liquidaciones {2, 3, 4} (9 variantes), con los parámetros de la base fijos.
   - El criterio ±20% usa las 4 variantes de un solo parámetro.
8. **Prueba anti look-ahead:** además de los tests sintéticos (cambiar el futuro no cambia decisiones pasadas), se ejecuta la especificación principal con la ejecución retrasada una vela (`sensibilidad`). Se informa; no es criterio del gate.
9. **Deslistado:** una serie cuya última vela cierra antes del fin del periodo.
10. **Huecos en las velas:**
    - Una salida pendiente espera a la siguiente vela del símbolo.
    - Una entrada sin vela en la apertura de ejecución se registra como `SIN_VELA`.
11. **Gap más allá de la liquidación:** el backtest ejecuta al precio de apertura del gap y no limita la pérdida al margen aislado. Es conservador.
12. **Régimen de una operación:** la etiqueta del día UTC de la entrada (vela diaria spot que abre ese día).
13. **Métricas:**
    - Esperanza por semestre (C-04) y por dirección (C-16).
    - El DSR usa N y V de las filas `principal` (H1, H2, H4-H1 y H4-H2), calculados cuando las cuatro están registradas.
14. **H4, `k`:** operaciones ejecutadas de la base cuya señal habría bloqueado el filtro, evaluado en la hora de señal de cada una.
15. **Sensibilidad v1 (ADR-013):**
    - Reglas de exposición (beta-ajustada, alts y posiciones) y de funding, con el tamaño recortado a los topes.
    - Beta = pendiente MCO de los rendimientos logarítmicos diarios del activo frente a BTC en los 90 días anteriores a cada reconstitución `D` (BTC = 1).
    - Funding = última liquidación normalizada a 8 h.
    - Depeg, ventana macro, volatilidad, liquidez y errores de la API no se evalúan.
16. **Corridas previstas** (declaradas antes de ejecutar):

    | Hipótesis | Principal | Robustez (rejilla) | Costes ×1.5 | Sensibilidad |
    |---|---|---|---|---|
    | H1-v1 | 1 | 26 | 1 | +1 vela |
    | H2-v1 | 1 | 242 | 1 | C-18, ADR-013 y +1 vela |
    | H4-H1-v1 | 1 | 8 | 1 | — |
    | H4-H2-v1 | 1 | 8 | 1 | — |

17. **Campo `prereg_commit` de `trials.csv`:** `4614d65…;aclaraciones=<hash del commit vigente de este documento>`.

## Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v1 | 2026-10-23 | Versión inicial, antes de cualquier dato o backtest |
| v1.1 | 2026-10-23 | Sección 6: detalles de implementación del backtester, escritos antes de descargar precios |
| v1.2 | 2026-10-23 | Sección 7: detalles de implementación y lista de corridas, escritos antes de cualquier backtest con datos reales |
