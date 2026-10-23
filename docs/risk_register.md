# Registro de riesgos

**Estado:** borrador F0 · **Fecha:** 23-oct-2026 · **Fuente:** plan maestro v2, CLAUDE.md, ADR-001 a 006
Probabilidad e impacto son **estimaciones** cualitativas (Alta / Media / Baja) que se revisan al cierre de cada fase.
El **disparador** es el hecho observable que activa la respuesta; la **respuesta** es lo que se hace cuando ocurre.

## Riesgos de estrategia y evidencia

| ID | Riesgo | Prob. | Impacto | Mitigación | Disparador | Respuesta |
|---|---|---|---|---|---|---|
| R01 | **No existe ventaja neta de costes**: ninguna hipótesis pasa el gate de la F4 | Alta | Alto | Pre-registro antes de resultados; gate estricto de la F4; costes y funding en todos los backtests; topes de parada del proyecto (PENDIENTE) | Ninguna de H1-H4 cumple el gate de la F4 | No avanzar a la F7; decidir con el propietario si se pre-registran hipótesis nuevas dentro de los topes o se detiene el proyecto |
| R02 | **Sobreajuste / data snooping** | Alta | Alto | Pre-registro fusionado con hash; `research/trials.csv` con todas las variantes; DSR ≥0.90 y PBO ≤0.30; holdout 2025-01-01 → hoy sellado | Variante probada sin anotar; DSR o PBO fuera de umbral; mirada al holdout antes del gate | Invalidar los resultados afectados; repetir con el número de pruebas real en el DSR |
| R03 | **Muestra insuficiente** (<200 operaciones fuera de muestra), sobre todo en H1 (solo BTC, 1d) | Media | Alto | Parámetros fijados a priori para que todo 2020-2024 cuente fuera de muestra (C-04); cortos permitidos; H2 con 8 alts líquidas; estimación teórica previa: ≈290 operaciones en H1 | El backtest principal da <200 operaciones | No relajar el umbral; la hipótesis no pasa. Ampliar universo solo con nuevo pre-registro |
| R04 | **Cambio de régimen**: la ventaja desaparece después de validarse | Media | Alto | Exigir ≥2 de 3 regímenes; F7 ≥12 semanas; piloto con capital pequeño; paradas por drawdown | Resultados de F7/F8 fuera del intervalo esperado del backtest | Volver a nivel B o detener la estrategia; análisis antes de reanudar |
| R05 | **Contaminación del holdout** | Baja | Alto | Holdout sellado; se abre una sola vez en el gate con aprobación explícita (CLAUDE.md regla 7) | Cualquier acceso a datos ≥2025-01-01 fuera del gate | Declarar el holdout quemado; registrar el incidente; nuevo periodo de validación |
| R06 | **Datos históricos de OI insuficientes** para H4 | **Ocurrido** | Medio | Verificado el 23-oct-2026: OI desde 2020-09 (BTC) y 2021-12 (ETH) | — | H4-v1 usa solo funding (H4-08); el OI puede probarse en una versión posterior con su propio pre-registro |
| R07 | **Muestra de nivel A insuficiente**: ningún setup llega a ≥100 casos calibrados | Alta | Bajo | El nivel A no existe hasta que los datos lo demuestren | Fin de la F7 sin setups certificados | Todo queda en nivel B (comportamiento previsto) |
| R08 | **Órdenes por debajo del nocional mínimo**: con USD 7.50 de riesgo y stops anchos, la orden no llega al mínimo del contrato (≈100 USDT en BTC) | Media | Medio | No se opera por debajo del mínimo y el backtest lo refleja (C-19); H1 solo en BTC para no repartir el riesgo | Proporción alta de señales "no ejecutables" en el backtest o en la F7 | Revisar stops o capital con un pre-registro o ADR nuevo; nunca subir el riesgo por operación sin ADR |

## Riesgos de mercado y apalancamiento

| ID | Riesgo | Prob. | Impacto | Mitigación | Disparador | Respuesta |
|---|---|---|---|---|---|---|
| R10 | **Gap o crash que salta el stop** (12-mar-2020: BTC cerca de −40% en un día) | Media | Alto | Margen aislado; apalancamiento efectivo ≤2× (F7-F8); distancia a liquidación ≥3× la del stop; stop STOP_MARKET reduce-only en el exchange; stress de costes ×1.5 | Pérdida realizada en una operación >1.5× el riesgo planificado | Revisar ejecución y slippage; pausar la estrategia hasta el análisis |
| R11 | **Liquidación** de una posición | Baja | Alto | Regla de distancia a liquidación ≥3× la del stop; margen aislado; veto del motor de riesgo | Precio de liquidación estimado a <3× la distancia al stop, o cualquier liquidación real | Veto pre-trade; si ocurre, incidente y parada del sistema |
| R12 | **Funding erosiona la ventaja** | Media | Medio | Funding incluido en los backtests; sin entradas con funding en contra por encima de un umbral (valor PENDIENTE) | Coste de funding acumulado >X% del beneficio bruto (umbral por definir en F4) | Revisar la estrategia; endurecer el filtro |
| R13 | **Correlación BTC-ETH** (≈0.8) duplica la exposición | Alta | Medio | BTC + ETH tratados como una sola exposición en el motor de riesgo | Intento de abrir BTC y ETH a la vez por encima del presupuesto de una operación | Veto del motor de riesgo |
| R14 | **Slippage de stops** en mercados rápidos y ADL | Media | Medio | Slippage explícito en backtests; stress ×1.5; tamaño pequeño | Slippage real medio > supuesto del backtest | Actualizar el modelo de costes y re-evaluar el gate |
| R15 | **Depeg de USDC** (capital en USDC; en mar-2023 cotizó cerca de 0.88) | Baja | Alto | Mantener en el exchange solo el capital de trading; vigilancia del precio | USDC < 0.98 sostenido | Pausar entradas; decisión del propietario |

## Riesgos de plataforma, regulación y fiscalidad

| ID | Riesgo | Prob. | Impacto | Mitigación | Disparador | Respuesta |
|---|---|---|---|---|---|---|
| R20 | **Futuros USDⓈ-M no disponibles** para la cuenta en México | Media | Alto | Verificación en la F1 (PENDIENTE, plan §8); Kraken como contingencia (ADR-002) | Cuestionario de derivados no disponible o no se puede abrir posición | Cambiar la parte de apalancamiento de plataforma o reducir el alcance a spot (ADR nuevo) |
| R21 | **Riesgo de contraparte o regulatorio** de Binance | Baja | Alto | Cuenta dedicada solo con el capital de trading; interfaz de ejecución propia para cambiar a la contingencia | Restricción regulatoria, congelación de retiros o caída prolongada | Detener operaciones; plan de contingencia |
| R22 | **Tratamiento fiscal de derivados** distinto al spot | Media | Medio | Revisión con el contador antes de la F8 (plan §1 #7) | Llegada a la F8 sin revisión fiscal | No empezar la F8 |
| R23 | **Caída del exchange o de la API** durante una posición abierta | Media | Medio | Stop reduce-only ya colocado en el exchange desde la entrada | Pérdida de conexión >N min con posición abierta (N por definir en F6) | Procedimiento del runbook (F6) |

## Riesgos de IA y de seguridad

| ID | Riesgo | Prob. | Impacto | Mitigación | Disparador | Respuesta |
|---|---|---|---|---|---|---|
| R30 | **El modelo inventa números o probabilidades** | Media | Alto | Claude solo emite JSON validado; los números los calcula código determinista (CLAUDE.md regla 3); salida inválida → `ABSTAIN` | Salida que no valida el esquema o incluye cifras fuera de lugar | `ABSTAIN` y registro en auditoría |
| R31 | **Inyección de instrucciones** desde noticias, webs o APIs | Media | Alto | Datos externos tratados como datos (CLAUDE.md regla 5); el motor de riesgo veta con independencia de Claude | Decisión del analista que cita instrucciones de una fuente externa | Descartar la decisión; revisar el saneado de entradas |
| R32 | **Cambio o retirada del modelo** altera el comportamiento del analista | Media | Medio | Versión fijada, prompt y esquema versionados (ADR-003); revisión mensual de deprecaciones | Aviso de deprecación o cambio de comportamiento en la evaluación | Migración con ADR y re-evaluación |
| R33 | **Fuga de claves API** | Baja | Alto | Claves sin retiro y con IP whitelist; SOPS/age; gitleaks en pre-commit y CI; nunca secretos en código, logs ni prompts | Alerta de gitleaks o actividad no reconocida | Revocar la clave de inmediato; rotar; incidente |
| R34 | **Activación accidental de ejecución real** | Baja | Alto | `LIVE_TRADING=false` por defecto; solo el propietario lo activa por CLI local con TOTP y commit firmado (CLAUDE.md regla 2); test que comprueba que está desactivado | Cualquier cambio de código que toque `LIVE_TRADING` | Bloqueo en revisión; incidente |
| R35 | **Error en el motor de riesgo** deja pasar una operación fuera de límites | Baja | Alto | Código puro con tests de casos normales, límites exactos y vetos; propiedades con hypothesis; cobertura ≥95% | Operación ejecutada que incumple un límite | Parada del sistema; incidente; test de regresión |
| R36 | **Autoejecución de nivel A errónea** | Baja | Alto | Mismo riesgo que nivel B; máximo 1 al día; apagado tras 2 pérdidas seguidas; ventana de veto de 20-30 min | 2 pérdidas seguidas de nivel A | Apagado automático del nivel A (previsto en ADR-006) |
| R37 | **Datos atrasados o feed caído** generan señales con precios viejos | Media | Medio | Bloqueo de entradas por datos atrasados en el motor de riesgo | Edad del dato > umbral configurado | Veto pre-trade y alerta |

## Riesgos de proyecto

| ID | Riesgo | Prob. | Impacto | Mitigación | Disparador | Respuesta |
|---|---|---|---|---|---|---|
| R40 | **Sobrecoste operativo**: ≈USD 120-130/mes (Max 5x + API, estimado) ≈ 8% mensual del capital, **sin tope de gasto** (ADR-008) | Alta | Medio | Presupuesto explícito; revisión mensual de gasto recomendada | Gasto acumulado sin hipótesis que pase la F4 | Decisión del propietario en la revisión mensual |
| R41 | **Retraso de calendario** con 20 h/semana, sin tope de calendario (ADR-008) | Media | Medio | Fases con criterios de salida (ADR-005); revisión mensual de avance | Fase que dura más del doble de lo estimado | Revisar el alcance de la fase con el propietario |
| R42 | **Coste de la API del analista** mayor de lo estimado (USD 5-15/mes) | Media | Bajo | Cuenta de API por consumo aparte (ADR-003); medir en la F5 | Coste mensual de la API > USD 30 | Reducir llamadas o cambiar de gama de modelo con ADR |
| R43 | **Disponibilidad del propietario** para el nivel B (señales de 4h de madrugada en México) | Alta | Medio | Ventana de validez de la señal (PENDIENTE, F6); nivel A solo con evidencia | Señales caducadas sin respuesta de forma recurrente | Revisar el horario operativo o el horizonte con ADR |
| R44 | **Iterar hasta que algo "funcione"**: sin topes, la tentación de probar variantes sin fin produce sobreajuste | Alta | Alto | ADR-008: cada especificación pre-registrada y contada en el N del DSR; el gate no se relaja; validación posterior al holdout en sombra (F7) | Especificación probada sin pre-registro o sin anotar en `trials.csv` | Invalidar el resultado; registrar el incidente |
