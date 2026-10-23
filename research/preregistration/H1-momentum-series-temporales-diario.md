# Pre-registro H1-v0: momentum de series temporales diario en BTC/ETH

- **ID:** H1 · **Versión:** v0 · **Prioridad:** Alta (plan §5)
- **Estado:** BORRADOR (decisiones abiertas H1-01 a H1-07 y comunes C-01 a C-18)
- **Fecha:** 2026-10-23 · **Autor:** borrador preparado para el propietario · **Aprobado por:** —
- **Commit de fusión:** `________`
- **Protocolo común:** `00-protocolo-comun.md` v0

## 1. Hipótesis

- **Enunciado [hipótesis]:** en BTC y ETH, la rentabilidad pasada en un horizonte de semanas predice el signo de la rentabilidad futura en un horizonte parecido, en ambas direcciones; una estrategia que se posiciona en la dirección de esa rentabilidad pasada tiene esperanza neta positiva después de comisiones de futuros, funding y slippage.
- **H0:** esperanza neta por operación ≤ 0. **Alternativa:** esperanza neta por operación > 0.
- **Base:** Liu y Tsyvinski, "Risks and Returns of Cryptocurrency", *Review of Financial Studies* (2021) (plan §5), que documentan momentum de series temporales en criptomonedas en horizontes de 1 a 4 semanas. **[por verificar]**: la especificación exacta del paper (frecuencia, horizonte de formación y de tenencia) se comprueba contra el texto antes de fijar H1-02.

## 2. Datos

- Velas diarias (cierre 00:00 UTC) de los perpetuos de BTC y ETH; contrato según C-01.
- Funding histórico de esos contratos.
- Periodo de investigación: inicio según C-03 → 2024-12-31. Holdout sellado: 2025-01-01 → fecha del gate.

## 3. Universo

- **[fijado, plan §5]** BTC y ETH. Sin otros activos.
- BTC y ETH cuentan como **una sola exposición** en el motor de riesgo (plan §3). Cómo se resuelve cuando ambos dan señal: H1-05.

## 4. Regla exacta

Estado actual: la regla tiene huecos que no se pueden rellenar sin decidir. Se escribe con los huecos marcados.

```
para cada activo A en {BTC, ETH}, al cierre de cada vela diaria t (00:00 UTC):
    señal_t = FUNCIÓN_SEÑAL(cierres de A hasta t inclusive, L)          # H1-01, H1-02
    si la evaluación toca en t según FRECUENCIA (H1-03):
        si señal_t > 0 y no hay largo abierto  -> ENTER_LONG en la apertura de t+1
        si señal_t < 0 y no hay corto abierto  -> ENTER_SHORT en la apertura de t+1
        si señal_t = 0 (zona neutral, si existe) -> salir y quedar plano     # H1-01
    stop inicial = STOP(precio de entrada, ATR, k)                       # H1-04
    salida = cambio de signo de la señal, o stop, o REGLA_SALIDA          # H1-04, H1-06
    tamaño = motor de riesgo (riesgo fijo por operación / distancia al stop)
```

- **4.2 Dirección:** largo y corto **[fijado, plan §5]**. Los cortos solo se habilitan si la hipótesis se valida en ambas direcciones (C-16).
- **4.6 Tamaño:** lo calcula el motor de riesgo (C-12).

## 5. Parámetros y rangos permitidos

Ningún valor está decidido. Las rejillas son candidatas para que el propietario elija.

| Parámetro | Rejilla candidata | Rango para la prueba ±20% | Pregunta |
|---|---|---|---|
| L: ventana de formación (días) | {7, 14, 21, 28} | cada valor ±20% | H1-02 |
| Frecuencia de evaluación | diaria / semanal (lunes 00:00 UTC) | — | H1-03 |
| n: ventana del ATR para el stop (días) | {14, 20} | ±20% | H1-04 |
| k: múltiplo de ATR del stop | {2, 3, 4} | ±20% | H1-04 |
| Zona neutral (si existe) | umbral sobre la rentabilidad de L días en unidades de volatilidad: {0, 0.5} | ±20% | H1-01 |

Número total de variantes: depende de las respuestas (con todas las rejillas de arriba serían 4 × 2 × 2 × 3 × 2 = 96).

## 6. Costes asumidos

Según el protocolo común (C-14): comisión taker en entrada y salida, funding histórico real en cada liquidación, slippage por lado y en stops; stress ×1.5 de todos los costes en el gate.

## 7. Protocolo de validación

Según C-04 (walk-forward), C-10 (PBO), C-11 (DSR) y C-15/C-16 (conteo y direcciones).

## 8. Métricas y gate de la F4

Gate del plan §5 sin cambios, con las definiciones del protocolo común (sección 1).

## 9. Criterios de invalidación

- Cualquier resultado sobre datos ≥2025-01-01 antes del gate.
- Cualquier variante fuera de la rejilla pre-registrada, o ejecutada sin anotarse en `trials.csv`.
- Cambiar la regla después de ver resultados (requiere H1-v1 y cuenta como pruebas adicionales).

## 10. Decisiones abiertas

| ID | Pregunta | Opciones | Recomendación (no es decisión) | Decisión del propietario |
|---|---|---|---|---|
| H1-01 | ¿Qué es la señal? | (a) Signo de la rentabilidad acumulada de L días (momentum de series temporales clásico): siempre largo o corto. (b) Cierre frente a su media móvil de L días. (c) Rentabilidad de L días dividida por su volatilidad, con zona neutral (plano si \|valor\| < umbral). | (a), por ser la definición de la literatura; (c) como segunda opción si se quiere reducir rotación | |
| H1-02 | ¿Qué valores de L se prueban? | (a) Solo uno, fijado ahora (por ejemplo 28 días). (b) Rejilla {7, 14, 21, 28}. (c) Otra. | Fijarlo tras verificar el paper; si se usa rejilla, cuenta para DSR y PBO | |
| H1-03 | ¿Con qué frecuencia se evalúa la señal? | (a) Diaria al cierre de 00:00 UTC. (b) Semanal (lunes 00:00 UTC), como en la referencia. | (b) si el paper usa datos semanales: menos rotación y menos costes; (a) da más operaciones | |
| H1-04 | ¿Cuál es el stop de protección? El motor de riesgo necesita un stop para dimensionar. | (a) k × ATR(n) desde la entrada, fijo. (b) k × ATR(n), que se mueve a favor (trailing). (c) Sin stop técnico: stop catastrófico amplio solo para el tamaño. | (a): es el más simple y no añade una segunda estrategia de salida | |
| H1-05 | BTC y ETH son una sola exposición. ¿Qué pasa si ambos dan señal? | (a) Solo se opera BTC; ETH no se opera en H1. (b) Se reparte el riesgo de una operación entre ambos (0.25% cada uno). (c) Se opera el primero que da señal; el otro espera. (d) Se investigan por separado sin la regla y la regla se aplica desde la F6 (contradice C-12a). | (b): conserva la muestra de ambos activos sin superar el riesgo de una exposición | |
| H1-06 | ¿Hay salida por tiempo o mínimo de permanencia? | (a) No; solo cambio de señal o stop. (b) Salida tras H días aunque no cambie la señal. | (a) | |
| H1-07 | Tras un stop, ¿cuándo se puede volver a entrar? | (a) Solo cuando la señal cambie de signo y vuelva. (b) En la siguiente evaluación si la señal sigue en la misma dirección. | (a): evita reentrar en la misma tendencia que acaba de fallar; reduce operaciones | |

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador inicial con decisiones abiertas |
