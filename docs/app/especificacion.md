# App Android: especificación funcional

**Estado:** v1 · **Fecha:** 23-oct-2026 · **Decisión de arquitectura:** ADR-010 · **Autonomía:** ADR-011

Principio de diseño: la app tiene que contestar en segundos tres preguntas: **¿estoy a salvo?**, **¿qué ha decidido el sistema y cómo le ha ido?** y **¿está aprendiendo de verdad?** Todo número lo calcula el backend con código determinista (`src/trading/reporting/`); la app solo lo muestra.

## 1. Pantallas

| Pantalla | Para qué |
|---|---|
| Resumen | Estado de seguridad y del dinero de un vistazo |
| Decisiones | Embudo completo, de la señal al resultado |
| Rendimiento | ¿Hay ventaja, y se parece a la del backtest? |
| Aprendizaje | Ficha de cada operación y evolución global |
| Controles | Kill switch, aprobar o vetar, niveles y pausas |
| Reportes | Descarga fiscal por año o mes |
| Chat | Preguntas de solo lectura a Claude sobre datos del sistema |

## 2. Resumen

- **Modo y escalón de autonomía** (ADR-011): investigación / sombra / nivel B / nivel A, con qué falta para el siguiente.
- **Semáforo de seguridad:** `LIVE_TRADING`, kill switch, frescura de datos y conexión con cada plataforma.
- **Capital total y por plataforma** (Binance, Hyperliquid); P&L de hoy, de la semana, del mes y total, en USD y en R.
- **Barras de límites** del plan §3: drawdown frente a 15% / 20%, pérdida diaria posible frente a 2%, semanal frente a 4%, apalancamiento efectivo frente a 2×, y exposición conjunta BTC+ETH.
- **Posiciones abiertas:** riesgo hasta el stop, distancia a liquidación y funding acumulado.
- **Próxima decisión:** hora del siguiente cierre de vela (4h / 1d) en hora de CDMX.

## 3. Decisiones: el embudo

Cuenta cada paso, por periodo y por estrategia:

```
señales de las reglas
  └─ decisión de Claude: ENTER_LONG · ENTER_SHORT · EXIT · HOLD · ABSTAIN
       └─ motor de riesgo: aprobadas · vetadas (por motivo: riesgo, apalancamiento, liquidación, datos…)
            └─ tú (nivel B): aprobadas · rechazadas · caducadas   |   nivel A: autoejecutadas · vetadas por ti
                 └─ ejecutadas → cerradas: ganadoras · perdedoras
```

Métricas que hacen el embudo útil, no solo bonito:

- **Valor añadido de Claude:** resultado medio (R) de lo que Claude decidió ejecutar frente al resultado **contrafactual** de lo que descartó (ABSTAIN o HOLD sobre una señal), medido en sombra. Si lo descartado rinde igual que lo ejecutado, Claude no está aportando.
- **Valor del motor de riesgo:** resultado contrafactual de las señales vetadas (¿los vetos evitaron pérdidas o costaron ganancias?).
- **Tu valor en nivel B:** resultado de lo que aprobaste frente a lo que rechazaste, y tiempo medio de respuesta y señales caducadas.
- **Acuerdo Claude-regla:** porcentaje de señales en que Claude sigue la regla, y resultado cuando discrepa.

## 4. Rendimiento

- Curva de capital y curva en R; drawdown.
- Esperanza neta en R con IC90%, profit factor, tasa de acierto, R medio de ganadoras y de perdedoras, racha máxima de pérdidas.
- Desglose por estrategia, activo, dirección, régimen (C-05) y plataforma.
- **Fuga de costes:** comisiones, funding y slippage reales frente a los modelados (C-14).
- **Deriva frente al backtest:** el resultado real dentro o fuera de la banda del Monte Carlo del backtest (semáforo). Fuera de banda baja un escalón de autonomía (ADR-011).

## 5. Aprendizaje

"Aprender" aquí significa **mejoras medidas**, no que el sistema se modifique solo en vivo (ADR-008).

### 5.1 Ficha de cada operación

1. **Contexto:** estrategia, señal, precio, indicadores, régimen y funding en el momento de la decisión.
2. **Razonamiento:** la justificación de Claude tal como se registró, con el modelo y la versión del prompt.
3. **Riesgo:** tamaño, R planificado, distancia a liquidación y vetos evaluados.
4. **Ejecución:** precio esperado frente al real (slippage en puntos básicos) en entrada y salida.
5. **Recorrido:** máxima excursión adversa y favorable (MAE / MFE) en R.
6. **Resultado:** P&L neto, R obtenido, motivo de salida, comisiones y funding.
7. **Etiquetas automáticas** (deterministas, calculadas en `trading.reporting.review`):
   - `SLIPPAGE_SOBRE_MODELO`: el slippage real superó el modelado.
   - `PERDIDA_MAYOR_QUE_R`: la pérdida superó 1.1 R (gap o deslizamiento en el stop).
   - `FUNDING_RELEVANTE`: el funding fue más del 10% del resultado bruto.
   - `GANANCIA_DEVUELTA`: llegó a +2 R y cerró en 0 R o menos.
   - `STOP_LIMPIO`: salió por stop con una pérdida de 1.1 R o menos.
8. **Nota de revisión:** texto de Claude o tuyo que solo puede citar los números de la ficha.

### 5.2 Evolución global

- Métricas en ventanas móviles (últimas 20 / 50 operaciones) para ver tendencia.
- Etiquetas más frecuentes y su coste acumulado en R: dónde se pierde dinero.
- Calibración de los setups candidatos a nivel A: frecuencia observada frente a la histórica.
- **Línea de tiempo de versiones:** hipótesis pre-registradas, gates superados o fallados, cambios de modelo y de prompt, con su efecto medido.

## 6. Controles

| Acción | Seguridad |
|---|---|
| Kill switch (bloquear entradas y cerrar posiciones) | Biometría |
| Pausar una estrategia o apagar el nivel A | Biometría |
| Rechazar o vetar una señal | Biometría |
| Aprobar una señal de nivel B / encender el nivel A | Biometría + TOTP |
| Activar `LIVE_TRADING` o cambiar límites de riesgo | **No disponible en la app** (reglas 2 y 4) |

## 7. Reportes fiscales

- Descarga en CSV (y PDF más adelante) por año o mes.
- Una fila por operación cerrada con: plataforma, instrumento, lado, fechas de apertura y cierre (UTC y hora de CDMX), cantidad, precios, comisiones, funding, P&L bruto y neto en USD, tipo de cambio aplicado y P&L neto en MXN.
- Totales: ganancias, pérdidas, resultado neto, comisiones y funding.
- **Por validar con el contador:** tipo de cambio (FIX de Banxico del día de cierre en CDMX, o el último publicado), tratamiento de derivados frente a spot y de operaciones en exchanges descentralizados. El reporte da los datos; la interpretación fiscal es del contador.

## 8. Chat de análisis

- Preguntas como "¿por qué se vetó la señal de ayer?" o "¿cómo me ha ido en cortos este mes?".
- Claude responde con los datos que le pasa el backend: no ejecuta nada ni inventa cifras, y trata las noticias y webs como datos (reglas 3 y 5).

## 9. API del backend (contrato inicial)

| Método y ruta | Devuelve |
|---|---|
| `GET /v1/resumen` | Modo, escalón, semáforo, capital, P&L, barras de límites, posiciones |
| `GET /v1/decisiones?desde&hasta` | Embudo y métricas de valor añadido |
| `GET /v1/rendimiento?desde&hasta&agrupar` | Resumen de rendimiento y desgloses |
| `GET /v1/operaciones/{id}` | Ficha de aprendizaje de una operación |
| `GET /v1/aprendizaje` | Evolución global y línea de tiempo |
| `GET /v1/reportes/fiscal?anio` | CSV fiscal |
| `POST /v1/controles/kill-switch` | Activa el kill switch (biometría) |
| `POST /v1/senales/{id}/aprobar` · `/rechazar` | Respuesta de nivel B (aprobar: biometría + TOTP) |
| `POST /v1/chat` | Respuesta de solo lectura |

Los modelos de datos de estas respuestas salen de `trading.audit` y `trading.reporting`.
