# ADR-011: Autonomía por evidencia

- **Estado:** Aceptado (decisión del propietario del 23-oct-2026)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan §4, §7; CLAUDE.md reglas 2, 3 y 4; ADR-006, ADR-008

## Contexto

El propietario quiere que el sistema llegue a operar solo y gestione el portafolio. Ante la opción de operar de forma autónoma con dinero real desde ya, eligió que la autonomía crezca con la evidencia.

## Decisión

"Operar solo" significa que **Claude decide, el motor de riesgo veta y el código ejecuta** con claves que solo pueden operar. Claude nunca tiene claves ni ejecuta directamente (regla 3). La autonomía avanza por escalones; cada escalón exige el anterior y su evidencia:

| Escalón | Qué hace el sistema solo | Condición para llegar |
|---|---|---|
| 0. Investigación | Nada con dinero; solo backtests pre-registrados | Hoy |
| 1. Sombra | Decide y "opera" en simulación con datos en vivo | Una hipótesis pasa el gate de la F4 |
| 2. Nivel B | Propone y el propietario aprueba cada operación real | F7 coherente con el backtest (≥12 semanas); propietario activa `LIVE_TRADING` (regla 2) |
| 3. Nivel A | Ejecuta solo los setups certificados, con ventana de veto, máx. 1/día | ADR-006: ≥100 casos calibrados y significativos |
| 4. Autonomía ampliada | Más autoejecuciones al día, más setups o gestión del reparto entre estrategias | ADR nuevo con evidencia de la F8/F9 |

- En todos los escalones el motor de riesgo mantiene el veto absoluto, y el propietario puede bajar de escalón al instante desde la app (ADR-010).
- Cualquier anomalía (pérdidas seguidas de nivel A, drawdown, deriva respecto al backtest) baja un escalón de forma automática.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Autónomo con dinero real desde ya | Rechazado por el propietario: sin evidencia, el riesgo de perder el capital es alto |

## Consecuencias

- El ritmo de autonomía lo marca la evidencia, no el calendario.
- La app muestra el escalón actual y qué falta para el siguiente.
