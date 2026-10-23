# Pre-registro HX-vN: título

- **ID:** HX · **Versión:** vN · **Prioridad:** Alta | Media | Baja (plan §5)
- **Estado:** BORRADOR | LISTO PARA FUSIONAR | FUSIONADO | RETIRADO
- **Fecha:** AAAA-MM-DD · **Autor:** · **Aprobado por:** propietario (fecha)
- **Commit de fusión:** `________` (se anota al fusionar en `main`; sin él no se puede hacer backtest)
- **Protocolo común:** `00-protocolo-comun.md` versión ___

> Ninguna sección se rellena mirando resultados. Si un dato no se conoce sin mirar resultados, queda como decisión abierta.

## 1. Hipótesis

- **Enunciado:** qué patrón se espera y por qué.
- **Hipótesis nula (H0):** la esperanza neta por operación, después de costes, es ≤ 0.
- **Hipótesis alternativa:** la esperanza neta por operación, después de costes, es > 0.
- **Base:** referencia académica o razonamiento, con lo que está verificado y lo que no.

## 2. Datos

- Fuente, instrumentos y frecuencia de velas.
- Periodo de investigación (inicio y fin) y holdout sellado (2025-01-01 → fecha del gate, CLAUDE.md regla 7).
- Tratamiento de huecos, velas incompletas y cambios de contrato.

## 3. Universo

- Instrumentos incluidos y criterio de inclusión **en cada fecha** (sin sesgo de supervivencia).
- Instrumentos excluidos y por qué.

## 4. Regla exacta

Pseudocódigo determinista que solo usa información disponible al cierre de la vela de señal.

- 4.1 Señal de entrada
- 4.2 Dirección (largo / corto / ambas)
- 4.3 Stop inicial (necesario para el tamaño por riesgo)
- 4.4 Salida
- 4.5 Reentrada y posiciones simultáneas
- 4.6 Tamaño: lo calcula el motor de riesgo (`src/trading/risk/`), nunca la estrategia

## 5. Parámetros y rangos permitidos

| Parámetro | Valor o rejilla pre-registrada | Rango permitido (±20% para la prueba de robustez) | Justificación |
|---|---|---|---|

Número total de variantes que se van a probar: ___ (todas se anotan en `trials.csv`).

## 6. Costes asumidos

| Coste | Supuesto | Fuente | Stress (gate) |
|---|---|---|---|
| Comisión de futuros | | | ×1.5 |
| Funding | | | ×1.5 |
| Slippage | | | ×1.5 |

## 7. Protocolo de validación

Walk-forward, ventanas, reoptimización y número de pruebas para DSR y PBO, según el protocolo común.

## 8. Métricas y gate de la F4

Copia literal del gate del plan §5 (no se modifica en un pre-registro), con las definiciones del protocolo común.

## 9. Criterios de invalidación

Qué invalida este pre-registro (por ejemplo, mirar el holdout, probar una variante no registrada).

## 10. Decisiones abiertas

| ID | Pregunta | Opciones | Recomendación | Decisión del propietario |
|---|---|---|---|---|

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
