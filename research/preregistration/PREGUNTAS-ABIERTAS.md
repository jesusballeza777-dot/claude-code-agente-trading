# Registro de decisiones del pre-registro

Antes era la lista de preguntas abiertas. El 23-oct-2026 el propietario delegó las decisiones en Claude
("avanza y termina el trabajo"). Todas están tomadas, justificadas en cada documento y **sin haber mirado
ningún resultado de backtest** (no se ha ejecutado ninguno). El propietario puede cambiar cualquiera
**antes de fusionar**; después de fusionar, un cambio es un pre-registro nuevo.

## Decisiones que más condicionan el resultado

| ID | Decisión | Dónde |
|---|---|---|
| C-04 | Parámetros fijados a priori, sin optimización; todo 2020-2024 es fuera de muestra | protocolo común |
| C-01 / C-03 | Perpetuos con margen en USDT, 2020-01-01 → 2024-12-31 (con margen en USDC solo hay datos desde 2024) | protocolo común |
| C-19 | Una orden por debajo del nocional mínimo no se ejecuta | protocolo común |
| H1-05 | H1 solo en BTC (exposición conjunta BTC+ETH y nocional mínimo) | H1 |
| H2-02 | Filtro de **expansión** de volatilidad: ATR(14) > ATR(100) | H2 |
| H2-06 | H2 sobre BTC, ETH y las 8 alts más líquidas (con solo BTC y ETH no llegaría a 200 operaciones) | H2 |
| H3-07 | H3 aplazada hasta la F9 | H3 |
| H4-08 | H4 solo con funding (el OI de ETH empieza en 2021-12) | H4 |

## Índice completo

| ID | Decisión | Documento |
|---|---|---|
| C-01 | Backtest con perpetuos con margen en USDT; operación según la F1 | `00-protocolo-comun.md` |
| C-02 | Ambas direcciones en perpetuos | `00-protocolo-comun.md` |
| C-03 | 2020-01-01 → 2024-12-31 | `00-protocolo-comun.md` |
| C-04 | Parámetros a priori, sin optimización | `00-protocolo-comun.md` |
| C-05 | Regímenes por media de 200 días de BTC; <20 operaciones no cuenta como positivo | `00-protocolo-comun.md` |
| C-06 | ±20%: esperanza > 0 en cada variante; costes ×1.5: IC90% > 0 | `00-protocolo-comun.md` |
| C-07 | Esperanza en R | `00-protocolo-comun.md` |
| C-08 | Bootstrap percentil, 10,000, semilla 20261023 | `00-protocolo-comun.md` |
| C-09 | Bootstrap por bloques mensuales | `00-protocolo-comun.md` |
| C-10 | CSCV con 16 particiones sobre la rejilla ±20% | `00-protocolo-comun.md` |
| C-11 | N del DSR = especificaciones principales de todas las hipótesis | `00-protocolo-comun.md` |
| C-12 | El backtest usa el motor de riesgo | `00-protocolo-comun.md` |
| C-13 | Supuestos de ejecución aceptados | `00-protocolo-comun.md` |
| C-14 | Taker 0.05%; slippage 0.05% BTC/ETH y 0.10% alts, doble en stops | `00-protocolo-comun.md` |
| C-15 | 200 operaciones en el total | `00-protocolo-comun.md` |
| C-16 | Gate total + esperanza > 0 en cada dirección | `00-protocolo-comun.md` |
| C-17 | Concentración mensual en R, meses UTC | `00-protocolo-comun.md` |
| C-18 | Entrada en la apertura siguiente + sensibilidad diurna informativa | `00-protocolo-comun.md` |
| C-19 | Nocional mínimo: no se opera por debajo | `00-protocolo-comun.md` |
| C-20 | Apalancamiento configurado en el exchange: 3× aislado | `00-protocolo-comun.md` |
| H1-01 | Signo de la rentabilidad de L días | `H1-momentum-series-temporales-diario.md` |
| H1-02 | L = 7 | `H1-momentum-series-temporales-diario.md` |
| H1-03 | Evaluación diaria | `H1-momentum-series-temporales-diario.md` |
| H1-04 | Stop fijo 2 × ATR(14) | `H1-momentum-series-temporales-diario.md` |
| H1-05 | Solo BTC | `H1-momentum-series-temporales-diario.md` |
| H1-06 | Sin salida por tiempo | `H1-momentum-series-temporales-diario.md` |
| H1-07 | Reentrada tras stop solo con cambio de señal | `H1-momentum-series-temporales-diario.md` |
| H2-01 | N = 60 velas | `H2-ruptura-canal-4h.md` |
| H2-02 | Filtro de expansión ATR(14) > ATR(100) | `H2-ruptura-canal-4h.md` |
| H2-03 | Stop fijo 2 × ATR(14) | `H2-ruptura-canal-4h.md` |
| H2-04 | Salida por canal opuesto de 20 velas | `H2-ruptura-canal-4h.md` |
| H2-05 | Reentrada solo con ruptura nueva | `H2-ruptura-canal-4h.md` |
| H2-06 | BTC, ETH y 8 alts líquidas | `H2-ruptura-canal-4h.md` |
| H2-07 | Máximo 1 posición por activo; el resto, el motor | `H2-ruptura-canal-4h.md` |
| H2-08 | Solo el grupo BTC+ETH | `H2-ruptura-canal-4h.md` |
| H3-01 a H3-06, H3-08 | Abiertas para la H3-v1 (H3 aplazada) | `H3-momentum-transversal-alts.md` |
| H3-07 | Aplazar H3 hasta la F9 | `H3-momentum-transversal-alts.md` |
| H4-01 | Sobre H1 y H2, dos pruebas | `H4-filtro-funding-oi.md` |
| H4-02 | Media de 3 liquidaciones, ±0.05% por 8h | `H4-filtro-funding-oi.md` |
| H4-03 / H4-04 | Sin OI; solo funding | `H4-filtro-funding-oi.md` |
| H4-05 | Bloqueo según la dirección | `H4-filtro-funding-oi.md` |
| H4-06 | Mejor que la base y que el p90 de filtros aleatorios | `H4-filtro-funding-oi.md` |
| H4-07 | Independiente del umbral de funding del motor | `H4-filtro-funding-oi.md` |
| H4-08 | Solo funding | `H4-filtro-funding-oi.md` |
