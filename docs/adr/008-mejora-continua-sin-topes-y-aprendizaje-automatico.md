# ADR-008: Mejora continua sin topes de parada del proyecto; aprendizaje automático como hipótesis pre-registrada

- **Estado:** Aceptado (decisión del propietario del 23-oct-2026). Las salvaguardas 2 a 5 aplican reglas que ya estaban en CLAUDE.md; las propuso Claude y el propietario puede ajustarlas con otro ADR.
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §3, §4, §8; CLAUDE.md reglas 3, 4, 6 y 7; ADR-005, ADR-006, ADR-007

## Contexto

- El plan §8 proponía detener el proyecto si, sin llegar a la F8, se alcanzaban 450 h de construcción, USD 900 de gasto operativo o 7 meses.
- El propietario rechazó esos topes el 23-oct-2026: *"quiero que avance hasta donde dé lugar; la idea es ir mejorando siempre los errores y hacer una red neuronal que aprenda a detectar esos patrones y mejore cada decisión"*.
- Iterar sin límite tiene un riesgo concreto: probar variantes hasta que una "funcione" produce resultados que no se repiten con dinero real (sobreajuste). Las reglas 6 y 7 de CLAUDE.md existen para evitarlo.

## Decisión

1. **Sin topes de parada del proyecto.** No hay límite de horas, gasto ni calendario: el proyecto sigue mientras el propietario lo decida.
2. **La protección del capital no cambia.** Siguen vigentes las paradas del sistema del plan §3 y del ADR-007: drawdown 15% / 20%, pérdida diaria 2% y semanal 4%, apalancamiento efectivo ≤2×. Son la protección de la cuenta, no un tope del proyecto.
3. **Mejorar = un ciclo con registro.** Cada mejora sigue el ciclo pre-registro → backtest → gate de la F4 → sombra (F7) → análisis de errores → pre-registro nuevo. Toda especificación probada cuenta en `research/trials.csv` y en el N del DSR, y el gate no se relaja nunca. Así una mejora real se distingue de una variante afortunada.
4. **Validación después del holdout.** El holdout 2025-01-01 → gate se abre una sola vez. Las hipótesis que se pre-registren después se validan con datos que no existían al pre-registrarlas: la simulación en sombra de la F7.
5. **Aprendizaje automático (incluidas redes neuronales) como hipótesis futura (H5 y siguientes):**
   - Es código: determinista en inferencia, con tests y versionado. Arquitectura, variables de entrada, objetivo, ventana de entrenamiento e hiperparámetros se pre-registran; cada configuración probada cuenta como una especificación en el DSR.
   - Solo se entrena con datos anteriores a cada ventana de prueba y nunca con el holdout.
   - Tiene que superar el gate de la F4 **y** batir, neto de costes, a la regla simple equivalente (H1, H2 o H4). Si no la bate, no se usa.
   - Su salida puede, como mucho, filtrar señales o alimentar la clasificación de nivel A del ADR-006. Nunca calcula tamaños ni se salta el motor de riesgo (CLAUDE.md regla 4).
   - Claude sigue sin asignar probabilidades (CLAUDE.md regla 3). Un modelo entrenado y validado es código, no el analista.
   - Requisitos previos: la canalización de datos de la F3 y los resultados de las hipótesis base de la F4, contra los que comparar.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Mantener los topes del plan §8 | Rechazado por el propietario |
| Iterar sin pre-registro ni conteo de pruebas | Garantiza sobreajuste; contradice CLAUDE.md reglas 6 y 7 |
| Empezar por la red neuronal | Con ≈11,000 velas de 4h por activo en 2020-2024, un modelo con muchos parámetros sobreajusta con facilidad; sin una regla simple de referencia no se puede saber si aporta algo |

## Consecuencias

- **Positivas:** el proyecto puede seguir aprendiendo de sus errores sin una fecha de corte arbitraria, y cada mejora queda medida contra lo anterior.
- **Negativas:** sin topes, el coste fijo (≈USD 120-130/mes con Max 5x más la API, **estimado**) sigue corriendo aunque no aparezca ventaja. Se recomienda que el propietario revise cada mes el gasto, las horas y el avance.
- **Pendiente:** pre-registrar H5 cuando estén disponibles los datos (F3) y los resultados base (F4).
