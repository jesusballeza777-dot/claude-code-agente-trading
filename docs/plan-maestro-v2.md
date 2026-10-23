# Plan Maestro v2: agente de trading cripto con Claude

**Estado:** Fase 0 en curso · **Última actualización:** 22-oct-2026
**Base:** Plan Maestro v1 (auditoría y plan F0-F9 del 22-oct-2026) más las decisiones del propietario de esta misma fecha.
No es asesoría financiera, legal ni fiscal. La rentabilidad no se da por supuesta: es la hipótesis que el sistema tiene que demostrar.

---

## 1. Decisiones del propietario (22-oct-2026)

| # | Tema | Respuesta del propietario | Decisión del plan |
|---|---|---|---|
| 1 | Capital de trading | USD 1,500 en USDC | Cuenta de Binance dedicada solo a esto. Riesgo por operación: 0.5% = USD 7.50 |
| 2 | Apalancamiento | Sí; es un objetivo del proyecto | Perpetuos USDⓈ-M de Binance. El apalancamiento sale del tamaño por riesgo, no de buscar más rentabilidad. Tope de 2× en F7-F8 y 3× en F9 (ver sección 3) |
| 3 | Tiempo | 20 h/semana | Calendario hasta capital real: ~5-6 meses |
| 4 | Plataforma | Ya tiene cuenta en Binance | Binance spot + futuros USDⓈ-M como plataforma principal. **Pendiente:** confirmar que los futuros están habilitados para su cuenta en México |
| 5 | Autonomía | Manual, pero automático en "oportunidades doradas" | Sistema por niveles A/B (sección 4) |
| 6 | Claude | Claude es el eje del proyecto | Recomendado: Claude Max 5x (USD 100/mes), que incluye créditos de API (por verificar en F1). Alternativa económica: Pro + API (~USD 50-60/mes) |
| 7 | Contador | Tiene experiencia en activos virtuales | Desbloquea la F8. Revisar con él el tratamiento fiscal de los derivados (distinto al spot) antes de la F8 |

## 2. Cambios respecto a v1

- **Mercado:** de spot 1× a **spot + perpetuos USDⓈ-M**, con largos y cortos.
- **Cortos permitidos:** las estrategias de tendencia operan en ambas direcciones, lo que casi duplica el número de señales y alivia el problema de muestra estadística.
- **Riesgo:** nuevas reglas para perpetuos: margen aislado, distancia a liquidación, funding y stop reduce-only en el exchange.
- **Ejecución:** sistema de aprobación por niveles A/B, con autoejecución condicionada en el nivel A.
- **Calendario:** se acorta por las 20 h/semana.
- **Presupuesto:** recalculado con Claude Max 5x.

## 3. Apalancamiento: principio y reglas

**Principio:** el apalancamiento no crea ventaja; multiplica la que haya, positiva o negativa, y las comisiones y el funding se pagan sobre el tamaño total de la posición. Por eso se determina por el tamaño basado en riesgo, nunca como objetivo en sí mismo.

Ejemplo con un riesgo fijo de USD 7.50 por operación:

| Distancia al stop | Tamaño de la posición | Apalancamiento efectivo |
|---|---|---|
| 2% | USD 375 | 0.25× |
| 0.5% | USD 1,500 | 1× |
| 0.25% | USD 3,000 | 2× |

| Regla del motor de riesgo | F7-F8 | F9 |
|---|---|---|
| Apalancamiento efectivo máximo (posición total / capital) | 2× | 3× (con ADR y evidencia) |
| Tipo de margen | Aislado, nunca cruzado | Aislado |
| Distancia a liquidación | ≥3 veces la distancia al stop | Igual |
| Stop | STOP_MARKET reduce-only en el exchange desde la entrada | Igual |
| Funding | Sin entradas si el funding en contra supera un umbral; funding incluido en el backtest | Igual |
| Cortos | Solo en estrategias validadas en ambas direcciones | Igual |
| Riesgo por operación | 0.5% (USD 7.50) | ≤1% |
| Pérdida diaria / semanal | 2% / 4% | 2% / 5% |
| Drawdown que detiene el sistema | 15% (USD 225); corte duro 20% (USD 300) | 20% |
| BTC + ETH | Una sola exposición (correlación ≈0.8) | Igual |

**Techo del plan: 3×.** Superarlo requiere un nuevo ADR con evidencia de la F9. Referencia de riesgo: el 12-mar-2020 BTC cayó cerca de un 40% en un día.

Claves API: lectura + trading spot + trading de futuros, **sin retiros**, con IP whitelist.

## 4. Aprobación por niveles ("oportunidades doradas")

- **Nivel B (normal):** cada señal llega por Telegram con el análisis y el propietario la aprueba o la rechaza manualmente.
- **Nivel A (certificado):** el **código**, no Claude, clasifica una señal como A solo si su tipo de setup tiene, en su histórico, esperanza neta y tasa de acierto calibradas y significativas (≥100 casos), confirmadas en la simulación en sombra (F7). Llega la alerta, hay **20-30 min para vetarla** y, sin respuesta, se ejecuta sola.
- **Mismo riesgo en ambos niveles.** El nivel A no da más tamaño ni más apalancamiento (solo se revisa en la F9, con datos reales).
- **Máximo 1 autoejecución al día.** El modo automático se apaga solo tras 2 pérdidas seguidas de nivel A, y el propietario puede apagarlo en cualquier momento.
- **El nivel A no existe hasta que los datos lo demuestren.** Si ningún setup llega a ese estándar, todo queda en nivel B.
- Claude nunca asigna probabilidades ni decide que una oportunidad es "dorada".

## 5. Hipótesis a pre-registrar (F0)

| ID | Hipótesis | Prioridad |
|---|---|---|
| H1 | Momentum de series temporales diario en BTC/ETH, en largo y en corto (base: Liu y Tsyvinski, RFS 2021) | Alta |
| H2 | Ruptura de canal en 4h con filtro de volatilidad, en ambas direcciones | Alta |
| H3 | Momentum transversal en alts líquidas: largo en las más fuertes y corto en las más débiles, neutral al mercado | Baja |
| H4 | Filtro de funding/OI extremo para *evitar* entradas cuando el mercado está demasiado apalancado | Media |

Gate de la F4 (sin cambios respecto a v1):
- ≥200 operaciones en walk-forward fuera de muestra.
- Esperanza neta con IC90% > 0.
- PF neto ≥1.25.
- DSR ≥0.90 y PBO ≤0.30.
- MaxDD p95 de Monte Carlo ≤25%.
- Sigue rentable con costes ×1.5 y parámetros ±20%.
- Positiva en ≥2 de 3 regímenes.
- Ningún mes aporta más del 30% del beneficio.
- En el holdout 2025-26, esperanza > 0 y PF ≥1.1.
- **Novedad:** comisiones de futuros y funding incluidos en todos los backtests.

## 6. Presupuesto actualizado

| Concepto | USD/mes |
|---|---|
| Claude Max 5x (API cubierta por los créditos, por verificar) | 100 |
| VPS en la UE y backups | 10-17 |
| Datos (en el MVP los de futuros de Binance son gratis) | 0 |
| **Total** | **~110-117 (MXN ~2,060-2,190 al FIX de 18.70)** |

Equivale al ~7.5% mensual del capital. Con USD 1,500, el proyecto es una inversión en construir y validar el sistema; en esta etapa no se paga solo.

## 7. Roadmap (20 h/semana)

| Fase | Duración aprox. |
|---|---|
| F0 Alcance y gobernanza | 1 sem |
| F1 Plataforma (incluye verificar futuros para MX) | 1 sem |
| F2 Fundaciones de ingeniería y seguridad | 1-2 sem |
| F3 Datos: spot + futuros, funding y OI | 2 sem |
| F4 Investigación cuantitativa | 4-5 sem |
| F5 Analista Claude (se solapa con F4) | 2 sem |
| F6 Riesgo y ejecución, incluidos perpetuos | 2 sem |
| F7 Shadow trading | ≥12 sem |
| F8 Piloto real con USD 1,500 | 3 meses |
| F9 Escala | Trimestral |

## 8. Pendientes para cerrar la F0

- [ ] **Topes de parada** propuestos. El proyecto se detiene si se cumple cualquiera sin llegar a la F8:
  - 450 h de construcción
  - USD 900 de gasto operativo
  - 7 meses de calendario

  *Pendiente de aceptación del propietario.*
- [ ] **Confirmar Futuros USDⓈ-M habilitados en Binance** (cuestionario de derivados superado y posibilidad de abrir una posición). Si no están disponibles para México, la parte de apalancamiento cambia de plataforma.
- [ ] Decidir entre Claude Max 5x y Pro + API.
- [ ] Después: documento de requisitos v2, ADR-001 a 006 (incluidos perpetuos y niveles A/B), pre-registro de H1-H4 y límites de riesgo firmados.
