# Decisiones abiertas del pre-registro

Índice de las preguntas que tiene que responder el propietario antes de fusionar los pre-registros.
Las opciones, el razonamiento y la recomendación están en cada documento; la recomendación **no** es una decisión.
Ningún pre-registro pasa a `LISTO PARA FUSIONAR` con preguntas sin responder.

## Las que más condicionan el resto

| ID | Pregunta | Por qué es prioritaria |
|---|---|---|
| H2-02 | ¿Qué es el filtro de volatilidad y en qué sentido filtra? | Las opciones son hipótesis opuestas (compresión vs expansión) |
| H1-01 / H1-03 | Definición de la señal de H1 y frecuencia de evaluación | Determinan rotación, costes y número de operaciones |
| H1-04, H2-03 | Stop de protección | El motor de riesgo dimensiona por distancia al stop |
| H1-05 | BTC y ETH como una sola exposición cuando ambos dan señal | Cambia la muestra de H1 a la mitad o no |
| C-01, C-02, C-03 | Contrato (margen USDT/USDC), spot o perpetuo para largos, inicio del periodo | Definen los datos de todas las hipótesis |
| C-04 | Walk-forward con o sin optimización | Define cuántas pruebas cuentan para DSR y PBO |
| C-16 | Qué exige "validada en ambas direcciones" | Decide si se pueden operar cortos |
| H3-07 | ¿Se aplaza H3? | Prioridad baja y encaje difícil con USD 1,500 |

## Índice completo

| ID | Pregunta | Documento |
|---|---|---|
| C-01 | Contratos del backtest y de la operación (margen USDT/USDC) | `00-protocolo-comun.md` |
| C-02 | Largos en spot o en perpetuos | `00-protocolo-comun.md` |
| C-03 | Inicio del periodo de investigación | `00-protocolo-comun.md` |
| C-04 | Esquema de walk-forward | `00-protocolo-comun.md` |
| C-05 | Definición de los 3 regímenes | `00-protocolo-comun.md` |
| C-06 | Qué significa "sigue rentable" en la robustez | `00-protocolo-comun.md` |
| C-07 | Unidad de la esperanza (R o %) | `00-protocolo-comun.md` |
| C-08 | Método del IC90% | `00-protocolo-comun.md` |
| C-09 | Método del Monte Carlo del MaxDD | `00-protocolo-comun.md` |
| C-10 | Método del PBO | `00-protocolo-comun.md` |
| C-11 | Número de pruebas del DSR | `00-protocolo-comun.md` |
| C-12 | ¿El backtest aplica el motor de riesgo? | `00-protocolo-comun.md` |
| C-13 | Supuestos de ejecución | `00-protocolo-comun.md` |
| C-14 | Valores de comisiones y slippage | `00-protocolo-comun.md` |
| C-15 | Cómo se cuentan las 200 operaciones | `00-protocolo-comun.md` |
| C-16 | Validación en ambas direcciones | `00-protocolo-comun.md` |
| C-17 | Cálculo de la concentración mensual | `00-protocolo-comun.md` |
| C-18 | Ventana de validez de la señal en el backtest | `00-protocolo-comun.md` |
| H1-01 | Definición de la señal | `H1-momentum-series-temporales-diario.md` |
| H1-02 | Valores de L | `H1-momentum-series-temporales-diario.md` |
| H1-03 | Frecuencia de evaluación | `H1-momentum-series-temporales-diario.md` |
| H1-04 | Stop de protección | `H1-momentum-series-temporales-diario.md` |
| H1-05 | BTC y ETH a la vez | `H1-momentum-series-temporales-diario.md` |
| H1-06 | Salida por tiempo | `H1-momentum-series-temporales-diario.md` |
| H1-07 | Reentrada tras un stop | `H1-momentum-series-temporales-diario.md` |
| H2-01 | Canal y N | `H2-ruptura-canal-4h.md` |
| H2-02 | Filtro de volatilidad | `H2-ruptura-canal-4h.md` |
| H2-03 | Stop inicial | `H2-ruptura-canal-4h.md` |
| H2-04 | Salida | `H2-ruptura-canal-4h.md` |
| H2-05 | Reentrada | `H2-ruptura-canal-4h.md` |
| H2-06 | Universo | `H2-ruptura-canal-4h.md` |
| H2-07 | Posiciones simultáneas | `H2-ruptura-canal-4h.md` |
| H2-08 | Grupos de correlación con alts | `H2-ruptura-canal-4h.md` |
| H3-01 | Criterio de universo | `H3-momentum-transversal-alts.md` |
| H3-02 | Señal de ranking | `H3-momentum-transversal-alts.md` |
| H3-03 | Construcción de la cartera | `H3-momentum-transversal-alts.md` |
| H3-04 | Frecuencia de rebalanceo | `H3-momentum-transversal-alts.md` |
| H3-05 | Stops en una cartera neutral | `H3-momentum-transversal-alts.md` |
| H3-06 | Qué cuenta como operación | `H3-momentum-transversal-alts.md` |
| H3-07 | Viabilidad con USD 1,500 | `H3-momentum-transversal-alts.md` |
| H3-08 | Límite de apalancamiento compartido | `H3-momentum-transversal-alts.md` |
| H4-01 | Estrategia base | `H4-filtro-funding-oi.md` |
| H4-02 | Definición de funding extremo | `H4-filtro-funding-oi.md` |
| H4-03 | Definición de OI extremo | `H4-filtro-funding-oi.md` |
| H4-04 | Combinación funding/OI | `H4-filtro-funding-oi.md` |
| H4-05 | Bloqueo según dirección | `H4-filtro-funding-oi.md` |
| H4-06 | Criterio de mejora frente a la base | `H4-filtro-funding-oi.md` |
| H4-07 | Relación con el umbral de funding del motor | `H4-filtro-funding-oi.md` |
| H4-08 | Plan B si falta histórico de OI | `H4-filtro-funding-oi.md` |
