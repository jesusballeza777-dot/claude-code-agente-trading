# Documento de requisitos v2

**Estado:** borrador para aprobación del propietario · **Fecha:** 23-oct-2026
**Fuente:** `docs/plan-maestro-v2.md` (22-oct-2026) y `CLAUDE.md`. Cada punto cita su sección de origen.
No es asesoría financiera, legal ni fiscal.

Etiquetas usadas: **[confirmado]** decisión del propietario o regla escrita en el plan/CLAUDE.md ·
**[estimado]** cifra aproximada del plan · **[hipótesis]** lo que el sistema tiene que demostrar ·
**[por verificar]** dato que se comprueba en una fase concreta · **PENDIENTE** punto abierto de la sección 8 del plan.

---

## 1. Objetivo

Construir y validar un agente de trading cripto en el que Claude actúa como analista y un código determinista
calcula, limita y ejecuta, para operar BTC, ETH y pocas alts líquidas en Binance spot y perpetuos USDⓈ-M
con un capital de USD 1,500 en USDC **[confirmado, plan §1]**.

- El objetivo de negocio es **demostrar con evidencia** (pre-registro, walk-forward, simulación en sombra) si existe
  una ventaja neta de costes antes de arriesgar capital real. La rentabilidad es una **[hipótesis]**, no un supuesto (plan, cabecera).
- Con USD 1,500 el proyecto es una inversión en construir y validar el sistema; en esta etapa no se paga solo **[estimado, plan §6]**.

## 2. Alcance

| Área | Incluido | Fuente |
|---|---|---|
| Mercados | Binance spot + perpetuos USDⓈ-M, largos y cortos | plan §2, ADR-001 |
| Activos | BTC, ETH y pocas alts líquidas | CLAUDE.md |
| Horizonte | Velas de 4h y 1d | plan §5 (H1 diario, H2 4h), ADR-004 |
| Hipótesis | H1-H4 pre-registradas antes de cualquier backtest | plan §5, CLAUDE.md regla 6 |
| Datos | Spot + futuros, funding y open interest (F3) | plan §7 |
| Analista Claude | Decisiones JSON validadas: `ENTER_LONG`, `ENTER_SHORT`, `EXIT`, `HOLD`, `ABSTAIN` | CLAUDE.md regla 3 |
| Motor de riesgo | Código puro con veto absoluto y los límites del plan §3 | CLAUDE.md regla 4, plan §3 |
| Ejecución | Aprobación por niveles A/B vía Telegram; stop STOP_MARKET reduce-only en el exchange desde la entrada | plan §3-4, ADR-006 |
| Validación | Gate de la F4, shadow trading ≥12 semanas (F7), piloto real de 3 meses (F8) | plan §5, §7 |
| Seguridad | Secretos con SOPS/age, gitleaks en pre-commit y CI, claves sin retiro y con IP whitelist | CLAUDE.md reglas 1 y 8, plan §3 |

## 3. Fuera de alcance

- Margen cruzado (siempre aislado) **[confirmado, plan §3]**.
- Apalancamiento efectivo por encima de 2× en F7-F8 o de 3× en F9; superar 3× requiere un ADR nuevo con evidencia de la F9 **[confirmado, plan §3]**.
- Cortos en estrategias que no se hayan validado en ambas direcciones **[confirmado, plan §3]**.
- Que Claude calcule tamaños, R/R, costes, apalancamiento, stops, límites o probabilidades, o que decida que una oportunidad es "dorada" **[confirmado, CLAUDE.md regla 3, plan §4]**.
- Cualquier código que llame a endpoints de retiro o transferencia **[confirmado, CLAUDE.md regla 8]**.
- Ejecución real antes de la F8 y sin la activación manual del propietario (CLI local con TOTP y commit firmado) **[confirmado, CLAUDE.md regla 2]**.
- Conexión a exchanges antes de la F1/F3 **[confirmado, CLAUDE.md]**.
- Más tamaño o apalancamiento en el nivel A que en el B (solo se revisa en la F9, con datos reales) **[confirmado, plan §4]**.
- Asesoría fiscal: el tratamiento de los derivados se revisa con el contador antes de la F8 **[confirmado, plan §1]**.
- Otros exchanges como plataforma principal (Kraken solo como contingencia; Bitso solo como rampa MXN) **[confirmado, ADR-002]**.

## 4. Supuestos

| # | Supuesto | Estado | Se verifica en |
|---|---|---|---|
| S1 | El propietario dispone de USD 1,500 en USDC en una cuenta de Binance dedicada | confirmado (plan §1) | F1 |
| S2 | Los futuros USDⓈ-M de Binance están habilitados para la cuenta en México (cuestionario de derivados superado y posibilidad de abrir posición) | **PENDIENTE** (plan §8) | F1 |
| S3 | Claude Max 5x incluye créditos de API suficientes para el analista | por verificar (plan §1, §6); probablemente **no**: la API se factura aparte (ver `docs/f1-verificacion-plataforma.md`) | F1 |
| S4 | El propietario dedica 20 h/semana | confirmado (plan §1) | seguimiento semanal |
| S5 | Los datos de futuros de Binance son gratuitos en el MVP | estimado (plan §6) | F3 |
| S6 | El histórico de funding y OI necesario para H4 está disponible con la profundidad suficiente | **confirmado en parte** (23-oct-2026, archivo público de Binance): funding desde 2020-01; OI desde 2020-09 (BTC) y 2021-12 (ETH). H4 usa solo funding | F3 |
| S7 | BTC y ETH tienen una correlación ≈0.8 y se tratan como una sola exposición | estimado (plan §3) | F4 |
| S8 | El contador del propietario revisa el tratamiento fiscal de los derivados antes de la F8 | confirmado (plan §1) | antes de F8 |
| S9 | El holdout 2025-01-01 → hoy permanece sellado hasta el gate de la F4 | confirmado (CLAUDE.md regla 7) | F4 |
| S10 | Las comisiones de futuros, el funding y el slippage se pueden modelar con suficiente precisión en el backtest | por verificar | F3-F4 |
| S11 | El nocional mínimo de orden permite operar con USD 7.50 de riesgo (≈100 USDT en BTCUSDT según fuentes secundarias) | por verificar | F1 |

## 5. KPIs del sistema

### 5.1 Gate de la F4 (investigación cuantitativa) — **[confirmado, plan §5]**

Una hipótesis pasa a la F5-F7 solo si cumple **todo** lo siguiente, con comisiones de futuros y funding incluidos en todos los backtests:

| KPI | Umbral |
|---|---|
| Operaciones en walk-forward fuera de muestra | ≥200 |
| Esperanza neta por operación | IC90% > 0 |
| Profit factor neto | ≥1.25 |
| Deflated Sharpe Ratio (DSR) | ≥0.90 |
| Probabilidad de sobreajuste (PBO) | ≤0.30 |
| MaxDD p95 de Monte Carlo | ≤25% |
| Robustez a costes ×1.5 y parámetros ±20% | sigue rentable |
| Regímenes con resultado positivo | ≥2 de 3 |
| Concentración temporal | ningún mes aporta >30% del beneficio |
| Holdout 2025-26 (se abre una sola vez) | esperanza > 0 y PF ≥1.1 |

La definición operativa de cada métrica (método del IC, regímenes, "sigue rentable", número de particiones del PBO, etc.)
está en `research/preregistration/00-protocolo-comun.md` (C-05 a C-17).

### 5.2 Riesgo (F6-F9) — **[confirmado, plan §3]**

| KPI | F7-F8 | F9 |
|---|---|---|
| Riesgo por operación | 0.5% (USD 7.50) | ≤1% |
| Apalancamiento efectivo máximo (posición total / capital) | 2× | 3× (con ADR y evidencia) |
| Distancia a liquidación | ≥3 × distancia al stop | igual |
| Pérdida diaria / semanal máxima | 2% / 4% | 2% / 5% |
| Drawdown que detiene el sistema | 15% (USD 225); corte duro 20% (USD 300) | 20% |
| Violaciones de límites que llegan al exchange | 0 (veto absoluto, CLAUDE.md regla 4) | 0 |
| Cobertura de tests del motor de riesgo | ≥95% (CLAUDE.md regla 4) | ≥95% |

### 5.3 Ejecución por niveles — **[confirmado, plan §4]**

| KPI | Valor |
|---|---|
| Casos históricos mínimos para certificar un setup como nivel A | ≥100, con esperanza neta y tasa de acierto calibradas y significativas, confirmadas en la F7 |
| Autoejecuciones de nivel A | máximo 1 al día |
| Ventana de veto del nivel A | 20-30 min |
| Apagado automático del nivel A | tras 2 pérdidas seguidas de nivel A |

### 5.4 Proyecto — **[estimado, plan §6-7]**

| KPI | Valor |
|---|---|
| Dedicación | 20 h/semana |
| Calendario hasta capital real | ~5-6 meses |
| Gasto operativo | ~USD 110-117/mes (MXN ~2,060-2,190 al FIX de 18.70), ~7.5% mensual del capital |
| Shadow trading (F7) | ≥12 semanas |
| Piloto real (F8) | 3 meses con USD 1,500 |

## 6. Criterios de parada

### 6.1 Parada del proyecto — **PENDIENTE de aceptación del propietario (plan §8)**

El proyecto se detiene si se cumple **cualquiera** de estos topes sin haber llegado a la F8:

| Tope | Valor propuesto | Estado |
|---|---|---|
| Horas de construcción | 450 h | PENDIENTE |
| Gasto operativo acumulado | USD 900 | PENDIENTE |
| Calendario | 7 meses | PENDIENTE |

### 6.2 Parada del sistema en operación — **[confirmado, plan §3-4]**

- Drawdown ≥15% (USD 225 con el capital inicial de USD 1,500): el sistema se detiene (sin nuevas entradas).
- Drawdown ≥20% (USD 300 con el capital inicial): corte duro.
- La base del drawdown (máximo histórico del capital o capital inicial) es una interpretación propuesta en ADR-007.
- Pérdida diaria ≥2% o semanal ≥4% (F7-F8): sin nuevas entradas hasta el siguiente periodo.
- Datos atrasados: sin nuevas entradas mientras dure el retraso (umbral propuesto en ADR-007, pendiente de aprobación).
- Nivel A: se apaga solo tras 2 pérdidas seguidas de nivel A; el propietario puede apagarlo en cualquier momento.

### 6.3 Parada de una hipótesis — **[confirmado, plan §5; CLAUDE.md reglas 6-7]**

- Una hipótesis que no pasa el gate de la F4 no avanza. No se re-optimiza sobre el holdout ni se prueba una variante
  sin anotarla en `research/trials.csv`.

## 7. Pendientes para cerrar la F0 (plan §8)

| Pendiente | Estado | Dónde se refleja |
|---|---|---|
| Topes de parada (450 h, USD 900, 7 meses) | **PENDIENTE** de aceptación | §6.1 |
| Confirmar Futuros USDⓈ-M habilitados en Binance para México | **PENDIENTE** (si no, la parte de apalancamiento cambia de plataforma) | S2, ADR-001, ADR-002 |
| Decidir entre Claude Max 5x y Pro + API | **PENDIENTE** | S3, ADR-003 |
| Documento de requisitos v2 | **PENDIENTE** de aprobación (este documento, en borrador) | — |
| ADR-001 a 006 | **PENDIENTE** de aprobación (redactados como "Propuesto") | `docs/adr/` |
| Pre-registro de H1-H4 | **PENDIENTE** de aprobación y fusión: H1, H2 y H4 en v1 "listo para fusionar" (decisiones delegadas en Claude el 23-oct-2026); H3 aplazada a la F9 | `research/preregistration/` |
| Límites de riesgo firmados | **PENDIENTE** de firma; codificados en `src/trading/risk/` | ADR-007 |
