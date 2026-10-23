# Pre-registro H3-v0: momentum transversal en alts líquidas, neutral al mercado

- **ID:** H3 · **Versión:** v0 · **Prioridad:** Baja (plan §5)
- **Estado:** BORRADOR (decisiones abiertas H3-01 a H3-08 y comunes C-01 a C-18)
- **Fecha:** 2026-10-23 · **Autor:** borrador preparado para el propietario · **Aprobado por:** —
- **Commit de fusión:** `________`
- **Protocolo común:** `00-protocolo-comun.md` v0

## 1. Hipótesis

- **Enunciado [hipótesis]:** entre las alts líquidas, las que más han subido en las últimas semanas siguen rindiendo más que las que más han caído; una cartera larga en las más fuertes y corta en las más débiles, neutral al mercado, tiene esperanza neta positiva después de costes y funding.
- **H0:** esperanza neta ≤ 0. **Alternativa:** esperanza neta > 0.
- **Base:** el plan no cita referencia para H3. Referencia candidata **[por verificar]**: Liu, Tsyvinski y Wu, "Common Risk Factors in Cryptocurrency", *Journal of Finance* (2022), sobre el factor momentum transversal en criptomonedas.

## 2. Datos

- Velas diarias de todos los perpetuos que hayan cumplido el criterio de universo en cada fecha, **incluidos los que después se deslistaron** (sin sesgo de supervivencia).
- Funding histórico de esos contratos.
- Periodo de investigación: inicio según C-03 → 2024-12-31. Holdout sellado: 2025-01-01 → fecha del gate.

## 3. Universo

- **[fijado, plan §5]** Alts líquidas: BTC y ETH quedan fuera de los rankings.
- Criterio de liquidez y tamaño del universo: H3-01.

## 4. Regla exacta

```
en cada fecha de rebalanceo r (H3-04):
    U_r      = alts que cumplen el criterio de universo en r (H3-01)
    puntuación(A) = RENTABILIDAD(A, ventana L, salto S) para A en U_r      # H3-02
    largos   = las k de mayor puntuación; cortos = las k de menor          # H3-03
    pesos    = PONDERACIÓN(largos, cortos), neutral según H3-03
    cerrar posiciones que salen de la cartera; abrir las nuevas
    stops    = STOP(...)                                                  # H3-05
```

- **4.2 Dirección:** largo y corto a la vez **[fijado, plan §5]**.

## 5. Parámetros y rangos permitidos

Ningún valor está decidido.

| Parámetro | Rejilla candidata | Rango para la prueba ±20% | Pregunta |
|---|---|---|---|
| Tamaño del universo | top 10 / 20 / 30 por volumen | ±20% | H3-01 |
| L: ventana de formación (días) | {7, 14, 21, 28} | ±20% | H3-02 |
| S: salto de los días más recientes | {0, 1} | — | H3-02 |
| k: posiciones por lado | {3, 5} | — | H3-03 |

## 6. Costes asumidos

Según el protocolo común (C-14), con el slippage de alts. La rotación semanal multiplica las comisiones; el funding de las alts puede ser extremo.

## 7. Protocolo de validación

Según C-04, C-10 y C-11. El conteo de "operaciones" para el mínimo de 200 se define en H3-06.

## 8. Métricas y gate de la F4

Gate del plan §5 sin cambios, con las definiciones del protocolo común.

## 9. Criterios de invalidación

Los mismos que H1, más: usar un universo construido con información posterior a la fecha de rebalanceo.

## 10. Decisiones abiertas

| ID | Pregunta | Opciones | Recomendación (no es decisión) | Decisión del propietario |
|---|---|---|---|---|
| H3-01 | ¿Criterio de universo? | (a) Las N alts con mayor volumen mediano de 30 días en perpetuos, excluidas stablecoins, con ≥90 días de histórico, N ∈ {10, 20, 30}. (b) Lista fija elegida ahora. | (a) con N = 20 | |
| H3-02 | ¿Señal de ranking? | (a) Rentabilidad de L días, L ∈ {7, 14, 21, 28}, sin salto. (b) Igual, saltando el último día (S = 1). (c) Rentabilidad ajustada por volatilidad. | (a) con un único L tras verificar la referencia | |
| H3-03 | ¿Construcción de la cartera y neutralidad? | (a) k largos y k cortos con igual peso, neutral en dólares. (b) Pesos inversos a la volatilidad. (c) Neutral a la beta frente a BTC. | (a) | |
| H3-04 | ¿Frecuencia de rebalanceo? | (a) Semanal, lunes 00:00 UTC. (b) Cada 2 semanas. | (a) | |
| H3-05 | ¿Stops? El motor de riesgo dimensiona por distancia al stop; una cartera neutral no encaja de forma natural. | (a) Stop por pata a k × ATR. (b) Sin stop por pata; stop de cartera (pérdida máxima de la cartera entre rebalanceos) y el riesgo por operación se define a nivel de cartera. | Necesita una adaptación del motor de riesgo (ADR) en cualquier caso | |
| H3-06 | ¿Qué cuenta como una "operación" para el mínimo de 200? | (a) Cada pata abierta y cerrada. (b) Cada rebalanceo de cartera. | (b): las patas de un mismo rebalanceo no son independientes | |
| H3-07 | **Viabilidad con USD 1,500.** Con apalancamiento ≤2× hay como mucho USD 3,000 brutos; con k = 5 son 10 patas de USD 300, cerca de los mínimos de orden de algunos contratos (por verificar). | (a) Seguir con H3 en la F4. (b) Aplazar H3 hasta la F9 (más capital) y no dedicarle horas ahora. | (b): prioridad baja, encaje difícil con el motor de riesgo y con el capital | |
| H3-08 | ¿Se cuentan las patas de H3 en el límite de apalancamiento compartido con H1/H2? | (a) Sí, un único límite de apalancamiento para todo el sistema. (b) Presupuesto separado. | (a): el límite del plan es por cuenta | |

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador inicial con decisiones abiertas |
