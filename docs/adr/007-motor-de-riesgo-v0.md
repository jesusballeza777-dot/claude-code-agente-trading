# ADR-007: Motor de riesgo v0: diseño e interpretación de los límites

- **Estado:** Aceptado (aprobado por el propietario el 23-oct-2026), incluidas las interpretaciones de la sección 3 y los umbrales de datos atrasados. Con esta aprobación quedan firmados los límites de riesgo de F7-F8
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §3; CLAUDE.md reglas 3 y 4; ADR-001; código en `src/trading/risk/`

## Contexto

- El motor de riesgo tiene veto absoluto, no depende de Claude, sus límites solo cambian con un ADR aprobado y su cobertura de tests debe ser ≥95% (CLAUDE.md regla 4).
- El plan §3 fija los límites, pero no define cómo se miden algunos de ellos (base del drawdown, si la pérdida diaria es reactiva o prospectiva, qué significa "una sola exposición" para BTC+ETH, si el tamaño por riesgo incluye costes).
- Los límites de riesgo todavía no están firmados (plan §8).

## Decisión

### 1. Forma del motor

- Código puro: sin red, sin reloj (la hora llega como argumento) y sin estado. Entradas inmutables y tipadas.
- Importes en `Decimal` con un contexto decimal propio (34 dígitos), independiente del contexto global del proceso. Horas siempre con zona horaria.
- Una entrada mal formada (precio no positivo, hora sin zona, perpetuo sin condiciones de margen) lanza una excepción al construirse: el flujo que la recibe no opera (fallo cerrado).
- Se evalúan **todas** las reglas y se devuelven **todos** los vetos que apliquen, para la auditoría. Se aprueba solo si no hay ninguno.
- Las comparaciones se hacen sin dividir (por ejemplo, `nocional ≤ 2 × capital`) para que los límites exactos no dependan del redondeo.

### 2. Configuración y techos

- Los valores operativos de F7-F8 están en `src/trading/risk/limits_f7_f8.toml`, versionado. Claves desconocidas o ausentes son un error.
- Los techos del plan están en código (`limits.py`) y ninguna configuración puede superarlos: riesgo por operación ≤1%, apalancamiento efectivo ≤3×, ratio liquidación/stop ≥3, pérdida diaria ≤2%, semanal ≤5%, drawdown ≤20%.

### 3. Interpretaciones aprobadas

| Límite (plan §3) | Interpretación implementada | Por qué |
|---|---|---|
| Riesgo por operación 0.5% | Pérdida si salta el stop **incluyendo comisión y slippage de entrada y salida** ≤ 0.5% del capital a mercado | Con costes cero reproduce la tabla del plan; con costes, la pérdida real en el stop no supera el presupuesto |
| Apalancamiento efectivo ≤2× | (nocional abierto de spot y perpetuos + nocional nuevo) / capital a mercado ≤ 2 | Definición del plan: posición total / capital |
| Distancia a liquidación ≥3× la del stop | Precio de liquidación estimado con la fórmula de margen aislado de Binance, con margen = nocional / apalancamiento configurado en el exchange; `|entrada − liquidación| ≥ 3 × |entrada − stop|` | El apalancamiento del exchange decide la liquidación; un stop al 2% exige liquidación a ≥6% (con margen de mantenimiento del 0.4%, como mucho ≈15× en el exchange) |
| Pérdida diaria 2% / semanal 4% | **Prospectiva:** pérdida ya incurrida en el periodo + riesgo hasta el stop de las posiciones abiertas + riesgo de la nueva ≤ límite × capital al inicio del periodo (00:00 UTC; lunes 00:00 UTC) | Si saltan todos los stops (sin gaps), el límite no se supera. Una versión reactiva solo bloquea cuando ya se ha superado |
| Drawdown 15% / 20% | Desde el **máximo histórico del capital**. ≥15% bloquea nuevas entradas; ≥20% bloquea y pide cerrar posiciones | Con USD 1,500 sin ganancias coincide con USD 225 / 300; protege también las ganancias |
| BTC + ETH una sola exposición | Riesgo hasta el stop de todas las posiciones de BTC y ETH + riesgo de la nueva ≤ riesgo de una operación (0.5%), sea cual sea la dirección | A tamaño completo equivale a "una posición a la vez"; una posición con stop en break-even (riesgo 0) libera el presupuesto |
| Cortos | Solo estrategias listadas en `short_enabled_strategies` (hoy vacía: ningún corto pasa); nunca en spot | Plan §3: cortos solo en estrategias validadas en ambas direcciones |
| Margen | Margen cruzado vetado | Plan §3 |

**Límites exactos:** en presupuestos (riesgo, apalancamiento, pérdidas, exposición conjunta) y en la distancia a liquidación, alcanzar exactamente el límite está permitido y superarlo se veta. En drawdown, alcanzar exactamente el umbral activa la parada. Los tests cubren ambos lados de cada límite.

### 4. Datos atrasados (no están en el plan; aprobados con este ADR)

Se veta la entrada si:

- el precio usado tiene más de **60 s**;
- la última vela cerrada tiene más de **intervalo de la vela + 5 min** (falta una vela que ya debería existir);
- alguna marca de tiempo está más de **5 s** en el futuro (desfase de reloj);
- los datos son de otro símbolo que la propuesta.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Límites como constantes en código, sin fichero | Menos auditable: el cambio de un valor se mezcla con cambios de lógica |
| `float` | El redondeo binario hace ambiguos los límites exactos |
| Pérdida diaria reactiva | Con varias posiciones abiertas se puede superar el límite solo con que salten los stops |
| Drawdown desde el capital inicial | No protege las ganancias acumuladas |
| BTC+ETH como "máximo una posición" | Equivalente a tamaño completo, pero no permite liberar el presupuesto con un stop en break-even |
| Tamaño por riesgo sin costes | La pérdida real en el stop superaría el 0.5% |

## Consecuencias

- **Positivas:** todos los límites del plan §3 que pidió el propietario están codificados, con tests de casos normales, límites exactos, vetos y propiedades (hypothesis), y 100% de cobertura de ramas en `risk/`.
- **Negativas:** la pérdida prospectiva y el drawdown desde máximos son más restrictivos que las lecturas alternativas; pueden reducir el número de operaciones.
- **Fuera de esta versión (PENDIENTE):**
  - Umbral de funding en contra (valor sin definir; ADR-001, H4-07).
  - Stop STOP_MARKET reduce-only en el exchange: es de la capa de ejecución (F6).
  - Latch de las paradas: el motor recibe `trading_halted`; persistirlo y exigir el rearme manual es de la F6.
  - Varias entradas en el mismo símbolo fuera del grupo BTC+ETH (piramidación): sin regla todavía.
  - Efectivo disponible para spot, cantidad mínima y paso de cantidad del contrato (datos del exchange, F6).
  - Depósitos y retiros manuales del propietario dentro de un periodo (ajuste del capital de inicio de periodo).
  - Riesgo de una cartera neutral (H3-05), si H3 sigue adelante.
  - Verificar la fórmula de liquidación contra la calculadora de Binance y los tramos de margen reales (F6).
