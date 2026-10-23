# ADR-003: Modelos de Claude: versión fijada y rol

- **Estado:** Aceptado (aprobado por el propietario el 23-oct-2026). El identificador exacto del modelo queda pendiente de comprobarse con la cuenta de API
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §1 (#6), §4, §6, §8; CLAUDE.md reglas 3, 4 y 5

> **Corrección del 23-oct-2026 (auditoría A-12):** este ADR afirmaba que las suscripciones no incluyen créditos de API. Es falso para Max: Max 5x incluye USD 100/mes en créditos de API para la consola ([centro de ayuda de Claude](https://support.claude.com/en/articles/17154008-api-credits-for-max-and-team-plans)). El analista se paga con esos créditos; ver `docs/presupuesto.md`. La decisión del ADR no cambia.

## Contexto

- Claude es el eje del proyecto **[confirmado, plan §1 #6]**, pero el modelo no calcula ni ejecuta: tamaños, R/R, costes, apalancamiento, stops y límites los calcula código determinista con tests **[confirmado, CLAUDE.md regla 3]**.
- Claude nunca asigna probabilidades ni decide que una oportunidad es "dorada" **[confirmado, plan §4]**.
- **Decidido el 23-oct-2026:** Claude Max 5x para el desarrollo con Claude Code y una cuenta de API por consumo, aparte, para el analista (las suscripciones no incluyen créditos de API, **por verificar** en la F1).
- Los modelos de la API tienen identificadores exactos y ciclos de vida: se publican nuevas versiones y las antiguas se deprecan y se retiran en fechas anunciadas **[confirmado]**. Un cambio de modelo puede cambiar el comportamiento del analista sin que cambie el código.
- En los modelos actuales no se pueden fijar parámetros de muestreo (temperatura), así que la salida no es determinista **[confirmado]**; la reproducibilidad se obtiene registrando entrada y salida, no repitiendo la llamada.

## Decisión

### Roles

| Rol | Fase | Qué hace | Qué no hace | Gama propuesta |
|---|---|---|---|---|
| **Analista** (runtime) | F5 en adelante | Lee el contexto preparado por código (señal, variables, datos de mercado) y emite una decisión JSON validada: `ENTER_LONG`, `ENTER_SHORT`, `EXIT`, `HOLD` o `ABSTAIN`, con una justificación en texto | Calcular números, asignar probabilidades, clasificar niveles A/B, saltarse el motor de riesgo | Opus (la de mayor capacidad disponible por API con la suscripción elegida) |
| **Asistente de desarrollo** (Claude Code) | Todas | Escribe código, tests y documentos bajo CLAUDE.md | Activar `LIVE_TRADING`, manejar secretos, decidir parámetros de hipótesis | No se fija por ADR: no interviene en decisiones de trading y todo lo que produce pasa por tests y revisión |

Un segundo modelo en runtime (por ejemplo, de gama Haiku para resumir noticias) **no se aprueba** en este ADR; si se necesita en la F5, requiere un ADR propio. Las noticias, webs y respuestas de APIs se tratan como datos, nunca como instrucciones (CLAUDE.md regla 5).

### Política de versión fijada

1. El analista usa **un identificador de modelo exacto**, escrito en configuración versionada. Prohibido usar un identificador genérico, un "latest" o elegir el modelo en tiempo de ejecución.
2. **Identificador exacto: PENDIENTE.** Se fija al crear la cuenta de API (F1), tras comprobarlo con el endpoint de listado de modelos (`GET /v1/models`) con esa cuenta.
3. Junto con el modelo se fijan y se versionan: el prompt de sistema (con hash), el esquema JSON de salida (con versión), el nivel de esfuerzo y el límite de tokens.
4. **Salida estructurada:** la respuesta se restringe a un esquema JSON y se valida en código. Cualquier salida inválida, una negativa del modelo (`stop_reason: "refusal"`), un error de red o un tiempo de espera agotado se convierten en `ABSTAIN`. Una decisión de Claude nunca llega al exchange sin pasar por el motor de riesgo, que tiene veto absoluto.
5. **Auditoría:** cada llamada registra identificador del modelo, hash del prompt, versión del esquema, entrada completa, salida completa y hora (UTC).
6. **Comprobación al arrancar (F5):** si el modelo fijado no está disponible, el analista emite `ABSTAIN` para todo y se alerta al propietario. Nunca se cambia de modelo automáticamente.
7. **Cambio de modelo:** solo mediante un ADR nuevo, tras repetir la evaluación de la F5 sobre el mismo conjunto de casos y comparar resultados. Durante la F7-F8 solo se cambia por retirada anunciada del modelo; la fecha del cambio se registra y los resultados en sombra se analizan por separado antes y después del cambio.
8. **Deprecaciones:** revisión mensual de los avisos de deprecación de Anthropic; la migración se planifica antes de la fecha de retirada.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Usar siempre el modelo más reciente | Cambia el comportamiento del analista sin control; invalida la evidencia de la F7 |
| Que Claude puntúe la confianza o la probabilidad | Prohibido por plan §4 y CLAUDE.md regla 3 |
| Varios modelos votando | Coste y complejidad sin evidencia de beneficio; reabrir con ADR si la F5 lo justifica |
| Sin Claude en runtime (solo reglas) | Contradice la decisión del propietario de que Claude sea el eje; las reglas siguen siendo la base y Claude solo filtra |

## Consecuencias

- **Positivas:** comportamiento del analista trazable y auditable; un cambio de modelo es explícito y revisado.
- **Negativas:** hay que seguir el ciclo de vida de los modelos y planificar migraciones; un modelo retirado obliga a re-evaluar.
- **Interacción con el nivel A (ADR-006):** si la decisión de Claude forma parte del setup (por ejemplo, Claude puede abstenerse), las estadísticas del setup dependen del modelo; un cambio de modelo obliga a revisar la certificación de nivel A.
- **Pendiente:** crear la cuenta de API y fijar el identificador exacto del modelo; medir el coste real del analista en la F5.
