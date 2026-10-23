# Pre-registro H2-v0: ruptura de canal en 4h con filtro de volatilidad

- **ID:** H2 · **Versión:** v0 · **Prioridad:** Alta (plan §5)
- **Estado:** BORRADOR (decisiones abiertas H2-01 a H2-08 y comunes C-01 a C-18)
- **Fecha:** 2026-10-23 · **Autor:** borrador preparado para el propietario · **Aprobado por:** —
- **Commit de fusión:** `________`
- **Protocolo común:** `00-protocolo-comun.md` v0

## 1. Hipótesis

- **Enunciado [hipótesis]:** cuando el precio cierra fuera de su rango reciente en velas de 4h y la volatilidad cumple una condición definida a priori, el movimiento tiende a continuar lo suficiente como para dejar esperanza neta positiva después de costes, en ambas direcciones.
- **H0:** esperanza neta por operación ≤ 0. **Alternativa:** esperanza neta por operación > 0.
- **Base:** familia de reglas de ruptura de canal (tipo Donchian) usadas en seguimiento de tendencia. No hay una referencia académica fijada en el plan para esta variante **[por verificar si el propietario quiere citar una]**.

## 2. Datos

- Velas de 4h (límites en 00, 04, 08, 12, 16 y 20 UTC) de los perpetuos del universo; contrato según C-01.
- Funding histórico de esos contratos.
- Periodo de investigación: inicio según C-03 → 2024-12-31. Holdout sellado: 2025-01-01 → fecha del gate.

## 3. Universo

- **PENDIENTE (H2-06).** El plan no lo fija para H2; el proyecto contempla BTC, ETH y pocas alts líquidas.
- BTC y ETH cuentan como una sola exposición (plan §3).

## 4. Regla exacta

```
para cada activo A del universo, al cierre de cada vela de 4h t:
    canal_alto_t = máximo de los máximos de las N velas anteriores a t (sin incluir t)   # H2-01
    canal_bajo_t = mínimo de los mínimos de las N velas anteriores a t (sin incluir t)
    filtro_t     = FILTRO_VOLATILIDAD(velas hasta t)                                     # H2-02
    si cierre_t > canal_alto_t y filtro_t y no hay largo abierto -> ENTER_LONG en la apertura de t+1
    si cierre_t < canal_bajo_t y filtro_t y no hay corto abierto -> ENTER_SHORT en la apertura de t+1
    stop inicial = STOP(...)                                                              # H2-03
    salida       = SALIDA(...)                                                            # H2-04
    tamaño       = motor de riesgo
```

- **[fijado, ADR-004]** La ruptura se evalúa con el **cierre** de una vela de 4h ya cerrada; no hay órdenes de entrada intra-vela sobre el nivel del canal.
- **4.2 Dirección:** largo y corto **[fijado, plan §5]**, sujeto a C-16.

## 5. Parámetros y rangos permitidos

Ningún valor está decidido.

| Parámetro | Rejilla candidata | Rango para la prueba ±20% | Pregunta |
|---|---|---|---|
| N: velas del canal de entrada | {20, 55} o {30, 60, 120} | ±20% | H2-01 |
| Parámetros del filtro de volatilidad | según la opción de H2-02 | ±20% | H2-02 |
| k: múltiplo de ATR del stop inicial | {2, 3} | ±20% | H2-03 |
| M: velas del canal de salida | {10, 20} | ±20% | H2-04 |

## 6. Costes asumidos

Según el protocolo común (C-14). En alts, slippage más alto que en BTC/ETH.

## 7. Protocolo de validación

Según C-04, C-10, C-11, C-15 y C-16.

## 8. Métricas y gate de la F4

Gate del plan §5 sin cambios, con las definiciones del protocolo común.

## 9. Criterios de invalidación

Los mismos que H1 (sección 9 de `H1-momentum-series-temporales-diario.md`).

## 10. Decisiones abiertas

| ID | Pregunta | Opciones | Recomendación (no es decisión) | Decisión del propietario |
|---|---|---|---|---|
| H2-01 | ¿Qué canal define la ruptura y con qué N? | (a) Máximo/mínimo de N velas de 4h, N ∈ {20, 55}. (b) N ∈ {30, 60, 120} (5, 10 y 20 días). (c) Un único N fijado ahora. | (c) con N = 60 (10 días) para limitar pruebas; o (b) si se prefiere rejilla | |
| H2-02 | ¿Qué es el "filtro de volatilidad" y en qué sentido filtra? El plan no lo define. | (a) **Compresión previa:** solo se opera si el ATR(14)/precio estaba en el tercil inferior de sus últimas 180 velas antes de la ruptura. (b) **Expansión:** solo si ATR(14) > ATR(100). (c) **Mínimo de volatilidad:** solo si ATR(14)/precio supera un umbral (evitar mercados muertos). (d) **Máximo de volatilidad:** no operar si ATR(14)/precio supera un umbral (evitar caos). | Pregunta clave: (a) y (b) son hipótesis opuestas. Elegir una sola para no duplicar pruebas | |
| H2-03 | ¿Stop inicial? | (a) k × ATR(14) desde la entrada. (b) El lado opuesto de un canal más corto (M velas). (c) Punto medio del canal de entrada. | (a): distancia al stop estable y fácil de dimensionar | |
| H2-04 | ¿Salida? | (a) Ruptura del canal opuesto de M velas (estilo Turtle). (b) Trailing de k × ATR desde el extremo favorable. (c) Salida por tiempo tras T velas. (d) Objetivo fijo en R. | (a), sin objetivo fijo: es coherente con una hipótesis de continuación | |
| H2-05 | Tras un stop, ¿cuándo se puede volver a entrar? | (a) Solo con una nueva ruptura posterior al stop. (b) En cualquier vela que cumpla la regla. | (a) | |
| H2-06 | ¿Universo? | (a) Solo BTC y ETH. (b) BTC, ETH y las K alts más líquidas (definición como en H3-01). | (a) para la primera versión: costes conocidos y datos más largos; (b) da más muestra | |
| H2-07 | ¿Cuántas posiciones simultáneas? | (a) Las que permita el motor de riesgo (apalancamiento ≤2×, pérdidas diaria/semanal). (b) Máximo 1 por activo y Q en total. | (a), con 1 por activo | |
| H2-08 | Si el universo incluye alts, ¿se agrupan por correlación además de BTC+ETH? | (a) No; solo BTC+ETH (plan §3). (b) Sí, con un umbral de correlación fijado ahora. | (a); ampliar requiere cambiar límites de riesgo mediante ADR | |

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador inicial con decisiones abiertas |
