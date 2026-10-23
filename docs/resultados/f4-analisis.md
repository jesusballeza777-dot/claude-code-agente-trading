# Análisis de los resultados de la F4 (2020-2024, holdout sellado)

- **Fecha:** 2026-10-23 · **Autor:** Claude, revisión pendiente del propietario.
- **Fuente:** `docs/resultados/f4-2020-2024.md` (generado), `research/results/gate-f4.json`, `research/trials.csv` (296 corridas).
- **Reglas:** pre-registro `4614d65` (congelado) + aclaraciones v1.2 (`61e5752`), escritas antes de cualquier backtest con datos reales.
- Todo lo de este documento se escribió **después** de ver resultados. Sirve para entenderlos y decidir los siguientes pasos; **no cambia ninguna regla ni el veredicto**. No es asesoría financiera, legal ni fiscal.

## 1. Veredicto

**Ninguna hipótesis pasa el gate de la F4.** Por tanto ninguna avanza a la sombra (F7), y el holdout sigue sellado: no tiene sentido abrirlo para una hipótesis que no pasa los criterios 1-8.

| Hipótesis | Operaciones | Esperanza neta | IC90% | Criterios 1-8 | Qué falla |
|---|---|---|---|---|---|
| H1-v1 (momentum diario BTC) | 127 | +0.103 R | [−0.089, +0.317] | 4 de 10 | Muestra (<200), IC, DSR, PBO, costes ×1.5, concentración mensual |
| H2-v1 (ruptura 4h + filtro) | 272 | +0.516 R | [+0.207, +0.847] | **9 de 10** | **PBO 0.456 > 0.30** |
| H4-H1-v1 (filtro funding) | 127 | +0.102 R | [−0.090, +0.317] | no evaluable | El filtro quita 1 operación de la base (< 20) |
| H4-H2-v1 (filtro funding) | 264 | +0.497 R | [+0.199, +0.825] | no evaluable | El filtro quita 9 operaciones de la base (< 20) |

## 2. H2-v1: casi, pero no

**Lo que cumple [confirmado en los datos]:**

- 272 operaciones, con esperanza neta de +0.516 R e IC90% por encima de 0. PF 1.86.
- DSR 0.992 con N = 4 especificaciones principales.
- MaxDD p95 de Monte Carlo: 19.2% (límite 25%).
- Con costes ×1.5, el límite inferior del IC90% sigue en +0.141 R.
- Todas las variantes ±20% de un solo parámetro tienen esperanza positiva.
- Es positiva en los tres regímenes: alcista +0.70 R (166 operaciones), bajista +0.31 R (57) y lateral +0.14 R (49).
- Ningún mes aporta más del 23.8% del beneficio.

**Lo que no cumple:** PBO = 0.456 (umbral ≤ 0.30). Es decir, en el 46% de las particiones CSCV la mejor variante de la rejilla dentro de muestra queda en la mitad inferior fuera de muestra.

**Lectura [hipótesis, posterior a los resultados]:**

- Con parámetros fijados a priori (C-04), el PBO se calcula sobre una vecindad de variantes parecidas (C-10), no sobre una búsqueda.
- Cuando las variantes son casi equivalentes, cuál es "la mejor" dentro de muestra es casi azar, y el PBO tiende a 0.5 aunque todas ganen dinero.
- Es posible que el criterio, aplicado así, sea estructuralmente difícil de pasar. Pero eso se ve **después** de mirar resultados: cambiar el criterio ahora sería mover la portería. Cualquier cambio requiere un protocolo v2 pre-registrado, cuenta como una especificación más en el N del DSR y **no rescata a H2-v1**.

**Advertencias [confirmado en los datos]:**

- **Asimetría por dirección:**
  - Largos: 166 operaciones, +0.898 R.
  - Cortos: 106 operaciones, −0.081 R.
  - C-16 no habilita cortos.
  - BTC pasó de USD 7,201 (cierre del 1-ene-2020) a USD 93,576 (31-dic-2024): el periodo fue muy alcista.
  - Una versión "solo largos" parecería mejor, pero esa idea sale de mirar los resultados. Solo es legítima como una hipótesis nueva pre-registrada, que cuenta en el N, y cuya evidencia limpia solo puede venir del holdout o de la sombra.
- **Variabilidad por semestre:** dos semestres negativos (2020-S1 −0.97 R y 2022-S2 −0.25 R) y semestres muy buenos (2021-S1 +3.0 R).
- **El motor de riesgo manda:**
  - Hubo 967 señales vetadas frente a 272 ejecutadas. Por motivo: pérdida diaria prospectiva 828, semanal 344, liquidación 250 y exposición BTC+ETH 112.
  - Lo que se evaluó es la estrategia *con* el motor, que es lo que se operaría (C-12).

**Sensibilidades (informativas, no forman parte del gate):**

| Variante | Operaciones | Esperanza | IC90% |
|---|---|---|---|
| Principal | 272 | +0.516 R | [+0.207, +0.847] |
| Costes ×1.5 | 273 | +0.428 R | [+0.141, +0.735] |
| C-18: entrada a las 16:00 UTC | 276 | +0.446 R | [+0.153, +0.761] |
| Reglas propuestas del ADR-013 | 271 | +0.509 R | [+0.201, +0.836] |
| Ejecución +1 vela (anti look-ahead) | 275 | +0.461 R | [+0.161, +0.783] |

- **ADR-013:** las reglas más restrictivas casi no cambian el resultado (141 vetos por funding en contra, 9 por máximo de posiciones). Es un argumento a favor de aprobarlo.
- **+1 vela:** la degradación es moderada, como cabe esperar de una señal de tendencia sin look-ahead. Los tests sintéticos comprueban además que cambiar el futuro no cambia las decisiones pasadas.

## 3. H1-v1: la orden mínima la dejó sin muestra

- La estimación previa era de ≈290 operaciones; se ejecutaron 127.
- **Causa [confirmado]:** con USD 1,500 y 0.5% de riesgo (USD 7.50), un stop de 2 × ATR(14) diario en BTC suele dar una orden por debajo del nocional mínimo supuesto (100 USDT).
  - Hubo 1,099 vetos por nocional mínimo, y 492 por liquidación demasiado cerca cuando el stop superaba ≈11% con 3× de apalancamiento en el exchange.
  - El pre-registro (H1-04) suponía que la orden quedaría por encima del mínimo "en la mayoría de los días". No fue así.
- Los largos ganan (+0.365 R) y los cortos pierden (−0.182 R).
- El nocional mínimo real del contrato es **por verificar en la F1**. Si fuera menor, H1 tendría más muestra. Pero eso sería otra especificación (H1-v2), que contaría en el N.

## 4. H4: no evaluable

- El filtro de funding (media de 3 liquidaciones ≥ 0.05%/8 h) habría quitado solo 1 operación de H1 y 9 de H2 (k < 20).
- El pre-registro lo declara **no evaluable** por falta de potencia (§7 de H4). No es un éxito ni un fracaso del filtro.
- El funding extremo fue poco frecuente en las señales ejecutadas.

## 5. Qué se puede decidir ahora (lo decide el propietario)

| Opción | Qué implica | Recomendación |
|---|---|---|
| A. Dar H1-H4 por cerradas como resultado negativo | Ninguna estrategia va a sombra. Se pre-registran hipótesis nuevas | Válido y honesto |
| B. Pre-registrar H2-v2 (por ejemplo solo largos, o con protocolo v2 del PBO) | Cuenta en el N del DSR. Su evidencia de 2020-2024 está contaminada (ya se vio), así que el juez sería el holdout (un solo uso) o la sombra de la F7 | **Recomendada**, con la sombra como juez principal y el holdout reservado |
| C. Revisar el protocolo del PBO (C-10) en un protocolo v2 | Aplica a pruebas futuras, no a H2-v1 | Recomendable junto con B, explicando el porqué antes de correr nada |
| D. Abrir el holdout para H2-v1 | No procede: H2-v1 no pasa los criterios 1-8 | **No** |

Nada de esto cambia los límites de riesgo ni acerca `LIVE_TRADING` a `true`.
