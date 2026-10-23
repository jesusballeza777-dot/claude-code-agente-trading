# ADR-006: Aprobación por niveles A/B

- **Estado:** Aceptado (aprobado por el propietario el 23-oct-2026)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §1 (#5), §4; CLAUDE.md reglas 2, 3 y 4

## Contexto

El propietario quiere operar de forma manual, pero con ejecución automática en "oportunidades doradas" **[confirmado, plan §1 #5]**. Hay que definir quién decide qué es una oportunidad de ese tipo y con qué salvaguardas, sin que Claude asigne probabilidades (CLAUDE.md regla 3).

## Decisión

1. **Nivel B (normal):** cada señal llega por Telegram con el análisis; el propietario la aprueba o la rechaza manualmente.
2. **Nivel A (certificado):** el **código**, no Claude, clasifica una señal como A solo si su tipo de setup tiene en su histórico esperanza neta y tasa de acierto calibradas y significativas (≥100 casos), confirmadas en la simulación en sombra (F7). Llega la alerta, hay **20-30 min para vetarla** y, sin respuesta, se ejecuta sola.
3. **Mismo riesgo en ambos niveles.** El nivel A no da más tamaño ni más apalancamiento; solo se revisa en la F9, con datos reales.
4. **Máximo 1 autoejecución al día.**
5. **Apagado automático** del modo A tras 2 pérdidas seguidas de nivel A; el propietario puede apagarlo en cualquier momento.
6. **El nivel A no existe hasta que los datos lo demuestren.** Si ningún setup llega a ese estándar, todo queda en nivel B.
7. Claude nunca asigna probabilidades ni decide que una oportunidad es "dorada".
8. Ambos niveles pasan por el motor de riesgo, que tiene veto absoluto, y ambos requieren `LIVE_TRADING` activado por el propietario (CLAUDE.md regla 2).

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Todo manual | Pierde las oportunidades fuera del horario del propietario; no cumple su decisión |
| Todo automático | Sin evidencia previa; contradice la decisión del propietario |
| Claude puntúa la confianza y decide el nivel | Prohibido (plan §4, CLAUDE.md regla 3); confianza no calibrada |
| Más tamaño en el nivel A | Aumenta el riesgo justo donde la evidencia es más reciente; se revisa solo en la F9 |

## Consecuencias

- **Positivas:** la autoejecución depende de evidencia estadística verificable, no del criterio del modelo; el riesgo no cambia entre niveles.
- **Negativas:** el nivel B depende de la disponibilidad del propietario (las velas de 4h cierran de madrugada en México, ADR-004).
- **PENDIENTE de definir (F6-F7), con ADR propio o actualización de este:**
  - Prueba estadística de "calibrada y significativa" (nivel de confianza, método).
  - Ventana de validez de las señales de nivel B.
  - Valor exacto de la ventana de veto dentro del rango de 20-30 min.
  - Seguridad del canal de Telegram (solo el chat del propietario, autenticación de las respuestas).
  - Si una decisión de Claude forma parte del setup, cómo afecta un cambio de modelo a la certificación (ADR-003).
