# ADR-013: Motor de riesgo v1: reglas ampliadas (exposición, alts, depeg, eventos macro, disyuntores, liquidez y funding)

- **Estado:** **Propuesto** (pendiente de aprobación del propietario). Mientras tanto, las reglas están activas en simulación, en sombra y como análisis de sensibilidad de los backtests. No son límites aprobados.
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto (lo propone Claude)
- **Fuentes:** CLAUDE.md regla 4; plan maestro v2.1 §3; ADR-001 punto 6; ADR-007; ADR-009 punto 4; auditoría A-05 a A-11; protocolo común C-14 y C-19; `research/preregistration/ACLARACIONES-v1.md`; código en `src/trading/risk/extended.py`, `limits_v1_propuesto.toml` y `explain.py`

## Contexto

El motor v0 (ADR-007) cubre el riesgo por operación, el apalancamiento, la liquidación, las pérdidas diaria y semanal, el drawdown, la exposición conjunta de BTC+ETH y los datos atrasados. La auditoría del 23-oct-2026 encontró huecos:

- **A-05.** H2 puede operar hasta 10 activos, y las alts también se mueven con BTC. El grupo BTC+ETH no limita la exposición total a cripto.
- **A-07.** El umbral de funding en contra seguía PENDIENTE (ADR-001 punto 6).
- **A-10.** No había reglas para el depeg de stablecoins, los eventos macro, los picos de volatilidad, los errores de la API ni la liquidez.

**Todas las reglas de este ADR son más restrictivas que el v0.** Ninguna relaja un límite aprobado (CLAUDE.md regla 4).

## Decisión propuesta

### 1. Reglas y valores

Los valores viven en `src/trading/risk/limits_v1_propuesto.toml`. Las fracciones son sobre el capital a mercado. La columna "Exacto" indica qué pasa cuando la cifra coincide justo con el límite.

| Regla | Valor propuesto | Veto | Exacto | Justificación |
|---|---|---|---|---|
| Exposición beta-ajustada | Σ \|nocional\| × \|β frente a BTC\| ≤ **100%** del capital | `BETA_EXPOSURE` | permitido | Ver 1.1 |
| Nocional por alt | ≤ **10%** del capital, sumando las posiciones del mismo activo | `ALT_NOTIONAL` | permitido | Ver 1.2 |
| Nocional en todas las alts | ≤ **25%** del capital | `ALTS_TOTAL_NOTIONAL` | permitido | Ver 1.2 |
| Posiciones simultáneas | ≤ **4** | `MAX_OPEN_POSITIONS` | 4 permitido; la 5.ª se veta | Ver 1.3 |
| Depeg de stablecoin | \|precio en USD − 1\| ≤ **0.5%** para USDT y USDC | `STABLECOIN_DEPEG`, más la señal `close_orderly` | 0.5% permitido | Ver 1.4 |
| Ventana macro | Sin entradas desde **2 h antes hasta 2 h después** de FOMC, CPI y NFP | `MACRO_EVENT_WINDOW` | bordes incluidos (±2 h exactas se vetan) | Ver 1.5 |
| Disyuntor de volatilidad | Volatilidad de 1h ≤ su **p99** | `VOLATILITY_CIRCUIT` | igual al p99 permitido | Ver 1.6 |
| Disyuntor de errores de la API | **3 errores en 10 min** detienen las entradas | `API_ERROR_CIRCUIT` | 3 errores saltan | Ver 1.6 |
| Spread | ≤ **5 pb** en BTC/ETH y ≤ **10 pb** en alts | `SPREAD_TOO_WIDE` | permitido | Ver 1.7 |
| Profundidad | Profundidad del lado consumido, dentro de 5 pb (BTC/ETH) o 10 pb (alts) del precio medio, ≥ **10 ×** el nocional | `BOOK_TOO_THIN` | permitido | Ver 1.7 |
| Funding en contra | ≤ **0.10% cada 8 h** | `ADVERSE_FUNDING` | permitido | Ver 1.8 |
| Datos de entrada | Si falta cualquier dato (beta, precio de stablecoin, calendario, funding) | `MISSING_CONDITION` | — | Fallo cerrado |

Además, en el motor v0 (sin cambiar ningún límite aprobado):

- **`BELOW_MIN_NOTIONAL` (A-06):** la orden por debajo del nocional mínimo del contrato se veta y nunca se aumenta el tamaño (C-19).
- **`LIQUIDATION_MODEL_UNAVAILABLE` (A-08):** cada perpetuo declara la fórmula de liquidación de su plataforma. Solo está implementada la de Binance USDⓈ-M en margen aislado; Hyperliquid se veta hasta que su fórmula esté implementada y verificada.
- **Periodos UTC (A-09):** `day_start` y `week_start` calculan los inicios de día y de semana (lunes 00:00 UTC).
- **Explicación (A-11):** cada veto lleva un código estable, la cifra observada y su límite. `explain()` lo convierte en un mensaje en español, por ejemplo: *"Esta operación arriesgaría USD 9.10 y tu límite por operación es USD 7.50"*.

### 1.1 Exposición beta-ajustada ≤ 100%

- El límite v0 de apalancamiento efectivo (2×) mide el nocional bruto, pero no distingue BTC de una alt con β = 1.4.
- Con una exposición beta-ajustada ≤ 100%, una caída de BTC que atraviese todos los stops (un gap) cuesta como mucho el mismo porcentaje del capital, multiplicado por la beta efectiva. Con 2× costaría el doble.
- Los peores días de BTC del periodo de investigación incluyen caídas de decenas de puntos porcentuales en un día (marzo de 2020) **[por verificar con los datos de la F3]**. Con 100%, un gap así deja la cuenta cerca del corte duro del 20% en lugar de muy por debajo.
- La beta frente a BTC (BTC = 1) la calcula el módulo `features` con datos anteriores a la decisión. Se usa \|β\|, y en bruto: un corto no compensa un largo, lo que es más restrictivo.

### 1.2 Alts: 10% por activo y 25% en total

- Una alt puede perder la mayor parte de su valor en horas por un hackeo, un deslistado o un colapso como el de LUNA en 2022. Con un tope del 10%, ese evento cuesta como mucho ≈10% del capital, y con el 25% conjunto, una ola de ventas de alts queda acotada.
- **Impacto en H2 [estimado]:** la ATR(14) de 4h de las alts suele estar entre 1.5% y 4% del precio, así que un stop de 2 × ATR queda entre 3% y 8%. El tamaño por riesgo (0.5%) da entonces un nocional del 6% al 17% del capital, y el tope del 10% recortaría las operaciones con stops por debajo del 5%.
- **El dimensionamiento recorta el tamaño al tope (nunca lo aumenta)**, y el veto queda como red de seguridad. El efecto real sobre H2 se medirá en la sensibilidad de la F4 (Ola 6).

### 1.3 Máximo 4 posiciones

- 4 × 0.5% de riesgo = 2%, el límite de pérdida diaria. El límite prospectivo del v0 ya impide más de 4 posiciones con todo su riesgo abierto.
- Pero cuando los stops pasan a breakeven, su riesgo restante es 0 y el v0 dejaría abrir más. El tope de 4 limita la exposición a un gap correlacionado y la carga operativa de vigilar posiciones.

### 1.4 Depeg de stablecoin

- USDC cotizó cerca de 0.88 en marzo de 2023 (registro de riesgos R15). La desviación normal de USDT y USDC es de décimas de punto básico a pocos puntos básicos **[estimado]**.
- Un umbral del 0.5% ignora el ruido y salta en un evento real. Además de vetar entradas, la regla emite `close_orderly`: una recomendación de cerrar las posiciones de forma ordenada, que no es el cierre inmediato del corte duro.
- La fuente del precio en USD (por ejemplo, USDT/USD y USDC/USD en un exchange con pares en dólares) se fija en la F6 **[por verificar]**.

### 1.5 Ventana macro de ±2 h

- FOMC (8 al año), CPI (mensual) y NFP (mensual) concentran movimientos bruscos en los activos de riesgo **[estimado]**.
- Con velas de 4h, una entrada justo antes del dato queda expuesta a un gap que atraviese el stop. ±2 h cubren el comunicado y la reacción inmediata.
- El calendario es un dato: se carga desde fuentes oficiales (Reserva Federal y BLS) en la F6 **[por verificar]**. Si el calendario cargado no cubre la ventana siguiente, el motor veta (`MISSING_CONDITION`).

### 1.6 Disyuntores

- **Volatilidad de 1h:** valor absoluto del rendimiento logarítmico de la última vela de 1h cerrada, comparado con el p99 de la misma medida en los 365 días anteriores, calculado *point-in-time* por `features`. Por construcción salta ≈1% de las horas.
- **Errores de la API:** 3 errores en una ventana de 10 min (la regla y su interfaz quedan definidas; se cablea en la F6, cuando exista la ejecución).

### 1.7 Liquidez

- El protocolo C-14 supone un slippage por lado de 0.05% (BTC/ETH) y 0.10% (alts).
- Un spread máximo de 5 pb y 10 pb hace que cruzar medio spread consuma como mucho la mitad del slippage supuesto: si el spread es mayor, el backtest no representa el coste real de ese momento.
- La profundidad se mide en la misma banda. Exigir 10 × el nocional significa que la orden consume como mucho el 10% del libro en esa banda.
- Con órdenes de USD 100 a 3,000 no debería saltar nunca en BTC/ETH **[estimado]**: protege en alts finas y en caídas bruscas.

### 1.8 Funding en contra ≤ 0.10% cada 8 h (ADR-001 punto 6; H4-07)

- El funding base de Binance es 0.01% cada 8 h; 0.10% es 10 veces el base y ≈110% anualizado.
- Coste en R por cada 8 h = funding ÷ distancia del stop. Con un stop del 3%, 0.10% cuesta ≈0.033 R cada 8 h, ≈0.1 R al día y ≈0.5 R en 5 días: se come la esperanza típica de una estrategia de tendencia **[estimado]**. Con el funding base el coste es ≈0.01 R al día, despreciable.
- El funding llega normalizado a 8 h (Hyperliquid liquida cada hora: se multiplica por 8). Positivo = pagan los largos.
- **Es independiente de H4** (decisión H4-07 b): H4 prueba un filtro de 0.05% como *señal*; esta regla es una *protección de coste*. Si H4 pasa el gate, el motor podrá adoptar su valor mediante otro ADR.

### 2. Dónde se aplican

| Contexto | Reglas |
|---|---|
| Sombra (F7) y operación real | `evaluate_entry_v1`: v0 + todas las reglas ampliadas |
| Backtest principal (F4) | Solo v0 con los límites firmados de F7-F8, como fija el pre-registro (ACLARACIONES-v1) |
| Backtest de sensibilidad (F4) | v0 + exposición y alts + funding: los únicos con datos históricos públicos fiables. El depeg, la ventana macro, la liquidez y los disyuntores no se evalúan en el histórico (no hay libro de órdenes ni calendario histórico verificado en el archivo público), y el informe lo dice |

### 3. Datos de entrada

Los calcula código determinista fuera del motor, que solo los recibe:

| Dato | Lo calcula | Disponible |
|---|---|---|
| β frente a BTC | `features` (rendimientos diarios, ventana *point-in-time*) | F3/F4 |
| Volatilidad de 1h y su p99 | `features` (velas de 1h) | F3/F4 |
| Funding vigente | archivo público (histórico) y endpoint público (F6) | F3 / F6 |
| Precio de las stablecoins en USD | F6 **[fuente por verificar]** | F6 |
| Calendario macro | F6 **[fuente por verificar]** | F6 |
| Libro de órdenes (spread y profundidad) | F6, por websocket público | F6 |
| Errores de la API | `execution` | F6 |

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| VaR con matriz de correlaciones | Más preciso en teoría, pero opaco, inestable con pocos datos y difícil de explicar en la app; la beta frente a BTC captura el factor dominante |
| Tope de nocional bruto sin beta | Más simple, pero trata igual a BTC que a una alt con β = 1.4 |
| Compensar largos con cortos | Menos restrictivo; ninguna estrategia tiene cortos validados |
| Topes por alt según su ATR | Un parámetro más que ajustar; se puede probar en una versión posterior con pre-registro |
| Ventana macro de ±30 min | Insuficiente con velas de 4h: la entrada ocurre al abrir la vela |
| Funding de 0.05% (el de H4) | Confundiría la protección de coste con la hipótesis H4, que aún no está validada (H4-07) |

## Consecuencias

- **Positivas:** la exposición a cripto queda acotada como un todo; los eventos anómalos bloquean entradas; cada veto se explica con cifras en la app; el fallo es cerrado si falta un dato.
- **Negativas:** menos operaciones de H2 y más pequeñas en alts. Además, cada dato nuevo es un punto de fallo: si su canalización se rompe, el sistema deja de operar. Es lo que se busca, pero obliga a vigilar los datos en la F6.
- **Pendiente:**
  - Aprobación del propietario (o ajuste de valores).
  - Fuentes del precio de las stablecoins y del calendario macro (F6).
  - Fórmula de liquidación de Hyperliquid (F6, ADR-009).
  - Medir en la sensibilidad de la F4 cuánto cambia H2.
