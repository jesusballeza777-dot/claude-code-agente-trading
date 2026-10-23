# Pre-registro H4-v1: filtro de funding extremo

- **ID:** H4 · **Versión:** v1 · **Prioridad:** Media (plan §5)
- **Estado:** LISTO PARA FUSIONAR (aprobado por el propietario; pendiente solo de la fusión en `main`)
- **Fecha:** 2026-10-23 · **Autor:** Claude, con decisiones delegadas por el propietario el 23-oct-2026 · **Aprobado por:** propietario, 23-oct-2026
- **Commit de fusión:** `________`
- **Protocolo común:** `00-protocolo-comun.md` v1

## 1. Hipótesis

- **Enunciado [hipótesis]:** las entradas en la dirección de un posicionamiento muy apalancado (funding muy positivo para largos, muy negativo para cortos) tienen peor esperanza neta que el resto; **descartarlas** mejora la estrategia base.
- H4 no es una estrategia: es un filtro que se prueba sobre H1 y sobre H2, como **dos pruebas separadas** (H4-H1 y H4-H2).
- **H0:** el filtro no mejora la esperanza neta de la base más que quitar al azar el mismo número de operaciones. **Alternativa:** sí la mejora.
- **Base:** razonamiento sobre posicionamiento abarrotado y liquidaciones en cascada; sin referencia académica fijada.

## 2. Datos

- Funding histórico de los perpetuos de la estrategia base (desde 2020-01, **confirmado**).
- **No se usa open interest** (H4-08): el histórico de OI empieza en 2020-09 para BTC y en 2021-12 para ETH (**confirmado**); usarlo recortaría el periodo de investigación casi a la mitad.
- Periodo e holdout: los de la estrategia base.

## 3. Universo

El de la estrategia base (H1: BTC; H2: BTC, ETH y 8 alts).

## 4. Regla exacta

```
para cada entrada que la estrategia base generaría en la vela t, con dirección D:
    f = media de las 3 últimas tasas de funding liquidadas antes del cierre de t,
        cada una normalizada a 8h (tasa × 8 / horas del intervalo de liquidación)
    si D = LARGO y f >= +0.05%  -> descartar la entrada ("filtrada")
    si D = CORTO y f <= -0.05%  -> descartar la entrada ("filtrada")
    en otro caso                -> la entrada sigue su curso normal (motor de riesgo, etc.)
```

- Solo se usa funding **ya liquidado** antes del cierre de `t` (sin la tasa estimada en curso).
- El filtro se aplica en cada vela en la que la regla base generaría la entrada. En H1, que se evalúa a diario, una entrada filtrada puede producirse un día después si el funding se normaliza y la señal sigue igual; en H2, una ruptura filtrada se pierde. Es la consecuencia directa de aplicar el filtro a la regla base sin cambiarla.

## 5. Parámetros

| Parámetro | Valor pre-registrado | Variantes ±20% |
|---|---|---|
| Umbral de funding (por 8h) | 0.05% | 0.04%, 0.06% |
| Liquidaciones promediadas | 3 | 2, 4 |

Especificaciones principales: **2** (H4-H1 y H4-H2), ambas cuentan en el DSR (C-11).

## 6. Costes asumidos

Los de la estrategia base (protocolo común, C-14).

## 7. Protocolo de validación

- La base y la filtrada se evalúan sobre el mismo periodo y con los mismos parámetros de la base.
- **Comparación con filtros aleatorios:** 10,000 filtros que quitan al azar el mismo número de entradas de la base (semilla 20261023).
- Si el filtro quita **menos de 20 entradas**, la prueba es **no evaluable** y H4 no pasa (falta de potencia, no éxito).

## 8. Métricas y gate

H4 pasa sobre una base si se cumplen las dos condiciones:

1. La estrategia filtrada pasa el gate completo del plan §5 por sí misma (incluidas ≥200 operaciones **después** de filtrar).
2. La esperanza neta por operación de la filtrada es mayor que la de la base **y** mayor que el percentil 90 de los 10,000 filtros aleatorios (H4-06).

## 9. Criterios de invalidación

Los mismos que H1, más: elegir el umbral mirando qué operaciones de la base perdieron.

## 10. Decisiones

| ID | Decisión | Justificación |
|---|---|---|
| H4-01 | (c) Sobre H1 y sobre H2, como dos pruebas | Ambas cuentan en el DSR |
| H4-02 | (c) Media de las 3 últimas liquidaciones, normalizada a 8h, umbral ±0.05% | Suaviza picos de una sola liquidación; 0.05% por 8h es 5 veces la tasa base habitual de 0.01% |
| H4-03 | (c) Sin OI | Ver H4-08 |
| H4-04 | (c) Solo funding | Consecuencia de H4-03 |
| H4-05 | (a) Bloqueo según la dirección | Lectura natural de "posicionamiento abarrotado" |
| H4-06 | (a) Mejor que la base y que el percentil 90 de filtros aleatorios, más el gate completo | Distingue una mejora real de quitar operaciones al azar |
| H4-07 | (b) Independiente del umbral de funding del motor de riesgo | El umbral del motor es una protección de coste y existe aunque H4 falle; puede adoptar el valor de H4 mediante ADR si H4 pasa |
| H4-08 | (a) H4 solo con funding | El OI recortaría el periodo (confirmado) |

## 11. Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador con decisiones abiertas (funding y OI) |
| v1 | 2026-10-23 | Decisiones tomadas por delegación del propietario; solo funding |
