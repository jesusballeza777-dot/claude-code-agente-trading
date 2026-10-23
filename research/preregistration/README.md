# Pre-registro de hipótesis

Regla 6 de CLAUDE.md: no se miran ni se generan resultados de backtest de una hipótesis antes de que su
pre-registro esté **fusionado** en esta carpeta con hash de commit. Toda variante probada se anota en `research/trials.csv`.

## Ciclo de vida de un pre-registro

| Estado | Significado | Se puede hacer backtest |
|---|---|---|
| `BORRADOR` | Tiene decisiones abiertas sin responder | No |
| `LISTO PARA FUSIONAR` | Todas las decisiones tomadas; falta la aprobación del propietario y la fusión | No |
| `FUSIONADO` | Fusionado en `main`; el hash del commit de fusión está anotado en el documento | Sí, solo con lo pre-registrado |
| `APLAZADO` | Se retomará en una fase posterior con una versión nueva | No |
| `RETIRADO` | Descartado antes de fusionar | No |

Las decisiones pueden tomarlas el propietario o Claude por delegación explícita del propietario; en ese caso el
documento lo dice. En ambos casos la fusión en `main` requiere la aprobación del propietario.

Un pre-registro fusionado no se edita. Cualquier cambio de regla, parámetro, universo o coste es un **pre-registro nuevo**
(nueva versión, `H1-v2`), y las pruebas hechas con la versión anterior siguen contando en `trials.csv` para el DSR.

## Contenido

| Fichero | Contenido | Estado |
|---|---|---|
| [`TEMPLATE.md`](TEMPLATE.md) | Plantilla de pre-registro | — |
| [`00-protocolo-comun.md`](00-protocolo-comun.md) | Datos, costes, validación y definiciones del gate comunes | v1 · LISTO PARA FUSIONAR |
| [`H1-momentum-series-temporales-diario.md`](H1-momentum-series-temporales-diario.md) | H1: momentum de series temporales diario en BTC | v1 · LISTO PARA FUSIONAR |
| [`H2-ruptura-canal-4h.md`](H2-ruptura-canal-4h.md) | H2: ruptura de canal en 4h con filtro de expansión de volatilidad | v1 · LISTO PARA FUSIONAR |
| [`H3-momentum-transversal-alts.md`](H3-momentum-transversal-alts.md) | H3: momentum transversal en alts, neutral al mercado | APLAZADO (F9) |
| [`H4-filtro-funding-oi.md`](H4-filtro-funding-oi.md) | H4: filtro de funding extremo sobre H1 y H2 | v1 · LISTO PARA FUSIONAR |
| [`PREGUNTAS-ABIERTAS.md`](PREGUNTAS-ABIERTAS.md) | Registro de todas las decisiones (antes, preguntas abiertas) | — |

## `research/trials.csv`

Una fila por cada variante ejecutada (incluidas las que fallan o se abandonan). Columnas:
`trial_id, fecha_utc, hipotesis_id, prereg_commit, variante, parametros_json, dataset_id, periodo_inicio, periodo_fin, tipo_muestra, n_operaciones, resultado_ref, autor, notas`.
Las filas con `tipo_muestra = principal` de todas las hipótesis forman el número de pruebas del Deflated Sharpe Ratio (C-11 del protocolo común).
