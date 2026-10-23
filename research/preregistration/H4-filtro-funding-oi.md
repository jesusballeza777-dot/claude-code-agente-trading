# Pre-registro H4-v0: filtro de funding/OI extremo

- **ID:** H4 · **Versión:** v0 · **Prioridad:** Media (plan §5)
- **Estado:** BORRADOR (decisiones abiertas H4-01 a H4-08 y comunes C-01 a C-18)
- **Fecha:** 2026-10-23 · **Autor:** borrador preparado para el propietario · **Aprobado por:** —
- **Commit de fusión:** `________`
- **Protocolo común:** `00-protocolo-comun.md` v0

## 1. Hipótesis

- **Enunciado [hipótesis]:** las entradas que se producen cuando el mercado está demasiado apalancado (funding u open interest extremos) tienen peor esperanza neta que el resto; **evitar** esas entradas mejora la estrategia base.
- H4 **no es una estrategia**, es un filtro sobre otra (plan §5: "para *evitar* entradas"). Se evalúa como "estrategia base + filtro" frente a "estrategia base".
- **H0:** el filtro no mejora la esperanza neta de la base más de lo que lo haría quitar al azar la misma proporción de operaciones. **Alternativa:** sí la mejora.
- **Base:** razonamiento sobre posicionamiento apalancado y liquidaciones en cascada; sin referencia académica fijada en el plan **[por verificar]**.

## 2. Datos

- Funding histórico de los perpetuos de la estrategia base.
- Open interest histórico. **[por verificar en F3]**: profundidad y granularidad del histórico de OI disponible; si no cubre el periodo de investigación, H4 se reformula (H4-08).
- Periodo de investigación y holdout: los de la estrategia base.

## 3. Universo

El de la estrategia base (H4-01).

## 4. Regla exacta

```
para cada señal de entrada de la estrategia base en la vela t, con dirección D:
    extremo_funding_t = CONDICIÓN_FUNDING(funding liquidado hasta t)       # H4-02
    extremo_oi_t      = CONDICIÓN_OI(OI hasta t)                           # H4-03
    bloqueo_t         = COMBINACIÓN(extremo_funding_t, extremo_oi_t, D)    # H4-04, H4-05
    si bloqueo_t: descartar la señal (se registra como "filtrada")
    si no: la señal sigue su curso normal (motor de riesgo, etc.)
```

- Solo se usa el funding **ya liquidado** antes del cierre de t (sin look-ahead sobre la tasa estimada en curso), salvo que H4-02 diga otra cosa.
- **4.2 Dirección:** la de la estrategia base.

## 5. Parámetros y rangos permitidos

Ningún valor está decidido.

| Parámetro | Rejilla candidata | Rango para la prueba ±20% | Pregunta |
|---|---|---|---|
| Umbral de funding | absoluto {0.05%, 0.10%} por 8h, o percentil {90, 95} de 90 días | ±20% | H4-02 |
| Ventana de funding | última liquidación / media de 3 liquidaciones | — | H4-02 |
| Medida de OI | variación de N días en z-score, N ∈ {3, 7}, umbral {2} | ±20% | H4-03 |

## 6. Costes asumidos

Los de la estrategia base (protocolo común, C-14).

## 7. Protocolo de validación

- La estrategia base y la filtrada se evalúan sobre las mismas ventanas de walk-forward (C-04).
- Comparación con un filtro aleatorio que quite la misma proporción de operaciones (H4-06).
- Las variantes del filtro cuentan como pruebas para el DSR (C-11).

## 8. Métricas y gate de la F4

- La estrategia filtrada tiene que pasar el gate completo del plan §5 por sí misma (incluido el mínimo de 200 operaciones **después** de filtrar).
- Además, el criterio de mejora frente a la base de H4-06.

## 9. Criterios de invalidación

Los mismos que H1, más: elegir el umbral mirando qué operaciones de la base perdieron.

## 10. Decisiones abiertas

| ID | Pregunta | Opciones | Recomendación (no es decisión) | Decisión del propietario |
|---|---|---|---|---|
| H4-01 | ¿Sobre qué estrategia base se aplica? | (a) H1. (b) H2. (c) Ambas, como dos pruebas separadas. | (c), contando ambas en el DSR | |
| H4-02 | ¿Qué es "funding extremo"? | (a) Umbral absoluto sobre la última tasa liquidada (por ejemplo, >0.05% por 8h, normalizado si el intervalo es otro). (b) Percentil de la tasa frente a los últimos 90 días. (c) Media de las últimas 3 liquidaciones frente a un umbral absoluto. | (c): suaviza picos de una sola liquidación | |
| H4-03 | ¿Qué es "OI extremo"? | (a) Variación del OI en N días, en z-score frente a 90 días. (b) OI / volumen. (c) No usar OI; solo funding. | (a), sujeto a H4-08 | |
| H4-04 | ¿Cómo se combinan funding y OI? | (a) Bloquea si ambos son extremos (Y). (b) Bloquea si cualquiera lo es (O). (c) Solo funding. | (a): reduce falsos positivos y no vacía la muestra | |
| H4-05 | ¿El bloqueo depende de la dirección? | (a) Sí: con funding muy positivo se bloquean solo largos; con funding muy negativo, solo cortos. (b) No: con mercado demasiado apalancado se bloquea cualquier entrada. | (a): es la lectura natural de "posicionamiento abarrotado" | |
| H4-06 | ¿Qué cuenta como "el filtro mejora"? | (a) Esperanza neta por operación de la filtrada > la de la base, y por encima del percentil 90 de 10,000 filtros aleatorios que quiten la misma proporción. (b) Mejora del MaxDD p95 sin empeorar la esperanza. (c) Ambas. | (a) | |
| H4-07 | ¿El umbral de H4 y el umbral de funding del motor de riesgo (ADR-001, "sin entradas si el funding en contra supera un umbral") son el mismo? | (a) Sí, el motor usa el umbral validado por H4. (b) No: el del motor es una protección de coste, independiente. | (b): el del motor existe aunque H4 falle; puede tomar el valor de H4 si pasa | |
| H4-08 | Si el histórico de OI no cubre el periodo de investigación (F3), ¿qué se hace? | (a) H4 solo con funding. (b) Recortar el periodo al disponible. (c) Aplazar H4. | (a), como nuevo pre-registro H4-v1 antes de mirar resultados | |

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador inicial con decisiones abiertas |
