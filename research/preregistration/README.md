# Pre-registro de hipótesis

Regla 6 de CLAUDE.md: no se miran ni se generan resultados de backtest de una hipótesis antes de que su
pre-registro esté **fusionado** en esta carpeta con hash de commit. Toda variante probada se anota en `research/trials.csv`.

## Ciclo de vida de un pre-registro

| Estado | Significado | Se puede hacer backtest |
|---|---|---|
| `BORRADOR` | Tiene decisiones abiertas sin responder | No |
| `LISTO PARA FUSIONAR` | Todas las decisiones abiertas resueltas por el propietario | No |
| `FUSIONADO` | Fusionado en `main`; el hash del commit de fusión está anotado en el documento | Sí, solo con lo pre-registrado |
| `RETIRADO` | Descartado antes de fusionar | No |

Un pre-registro fusionado no se edita. Cualquier cambio de regla, parámetro, universo o coste es un **pre-registro nuevo**
(nueva versión, `H1-v2`), y las pruebas hechas con la versión anterior siguen contando en `trials.csv` para el DSR.

## Contenido

| Fichero | Contenido | Estado |
|---|---|---|
| [`TEMPLATE.md`](TEMPLATE.md) | Plantilla de pre-registro | — |
| [`00-protocolo-comun.md`](00-protocolo-comun.md) | Datos, costes, validación y definiciones del gate comunes a todas las hipótesis | BORRADOR |
| [`H1-momentum-series-temporales-diario.md`](H1-momentum-series-temporales-diario.md) | H1: momentum de series temporales diario en BTC/ETH | BORRADOR |
| [`H2-ruptura-canal-4h.md`](H2-ruptura-canal-4h.md) | H2: ruptura de canal en 4h con filtro de volatilidad | BORRADOR |
| [`H3-momentum-transversal-alts.md`](H3-momentum-transversal-alts.md) | H3: momentum transversal en alts líquidas, neutral al mercado | BORRADOR |
| [`H4-filtro-funding-oi.md`](H4-filtro-funding-oi.md) | H4: filtro de funding/OI extremo | BORRADOR |
| [`PREGUNTAS-ABIERTAS.md`](PREGUNTAS-ABIERTAS.md) | Índice de todas las decisiones que tiene que tomar el propietario | — |

## `research/trials.csv`

Una fila por cada variante ejecutada (incluidas las que fallan o se abandonan). Columnas:
`trial_id, fecha_utc, hipotesis_id, prereg_commit, variante, parametros_json, dataset_id, periodo_inicio, periodo_fin, tipo_muestra, n_operaciones, resultado_ref, autor, notas`.
El número de filas por hipótesis alimenta el número de pruebas del Deflated Sharpe Ratio.
