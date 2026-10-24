# Plan Maestro v2.1: agente de trading cripto con Claude

**Estado:** vigente · **Fecha:** 23-oct-2026 · **Sustituye a:** `plan-maestro-v2.md` (queda como histórico, sin cambios)
**Por qué existe:** el v2 mostraba como abiertas decisiones que ya se tomaron (auditoría A-14). Este documento recoge el estado real; cada punto remite al ADR que lo decide.
No es asesoría financiera, legal ni fiscal. La rentabilidad no se da por supuesta: es la hipótesis que el sistema tiene que demostrar.

Etiquetas: **[confirmado]** · **[estimado]** · **[hipótesis]** · **[por verificar]**.

---

## 1. Decisiones del propietario

| # | Tema | Decisión vigente | Fuente |
|---|---|---|---|
| 1 | Capital | USD 1,500 en USDC; riesgo por operación 0.5% = USD 7.50 **[confirmado]** | plan v2 §1, ADR-007 |
| 2 | Apalancamiento | Perpetuos USDⓈ-M; se deriva del tamaño por riesgo; tope 2× en F7-F8 y 3× en F9 **[confirmado]** | ADR-001, ADR-007 |
| 3 | Tiempo | 20 h/semana **[confirmado]** | plan v2 §1 |
| 4 | Plataformas | Binance (spot + USDⓈ-M), Hyperliquid con wallet de agente sin retiros, Kraken de contingencia, Bitso como rampa MXN | ADR-002, ADR-009 |
| 5 | Autonomía | Niveles A/B, que crecen por escalones según la evidencia | ADR-006, ADR-011 |
| 6 | Claude | Max 5x, que incluye USD 100/mes en créditos de API **[confirmado]**; versión del modelo fijada al crear la cuenta | ADR-003, `presupuesto.md` |
| 7 | Contador | Revisión fiscal de derivados y de Hyperliquid antes de la F8 | plan v2 §1, `f1-verificacion-plataforma.md` |
| 8 | Topes del proyecto | **Rechazados:** mejora continua sin topes de horas, gasto ni calendario; la protección del capital no cambia | ADR-008 |
| 9 | Interfaz | **Centro de Mando web** como app principal; la app Android queda como cliente ligero (alertas y kill switch) | ADR-010, ADR-014 |
| 10 | Copiloto de la app | Se llama **Brújula** | decisión del 23-oct-2026 |

## 2. Cambios respecto a v2

- Todos los pendientes de la §8 del v2 están resueltos, salvo la verificación de los futuros para México (F1, la hace el propietario).
- Se añaden Hyperliquid, la autonomía por evidencia, el Centro de Mando, la mejora continua sin topes y el aprendizaje automático como hipótesis futura (ADR-008 a 014).
- Presupuesto unificado en `docs/presupuesto.md` (≈USD 110-117/mes).
- Motor de riesgo v1 **propuesto** con reglas más restrictivas (ADR-013); activo en simulación y en sombra mientras se aprueba.
- Salvaguardas metodológicas **en código**: guardia del holdout y registro obligatorio de pruebas (auditoría A-01, A-02).

## 3. Riesgo

**Límites firmados de F7-F8** (ADR-007, `src/trading/risk/limits_f7_f8.toml`): riesgo por operación 0.5%, apalancamiento efectivo ≤2×, distancia a liquidación ≥3× la del stop, pérdida diaria 2% y semanal 4%, drawdown 15% (parada) y 20% (corte duro), BTC+ETH como una exposición, margen aislado, cortos solo en estrategias validadas en ambas direcciones y datos atrasados vetados. **Techo del plan: 3×.**

**Propuestos (ADR-013, pendientes de aprobación):** exposición agregada ajustada por beta frente a BTC, límites por alt y total en alts, máximo de posiciones, depeg de stablecoins, ventana de eventos macro, circuit breakers, liquidez mínima, umbral de funding en contra y nocional mínimo.

Claves API: lectura y trading, **sin retiros**, con IP whitelist. MetaMask nunca se conecta al sistema.

## 4. Aprobación por niveles y autonomía

Sin cambios respecto al v2 §4 (ADR-006). Los escalones de autonomía están en ADR-011: investigación → sombra → nivel B → nivel A → autonomía ampliada. Claude nunca asigna probabilidades ni decide que una oportunidad es "dorada".

**Evaluación del analista Claude (nuevo, auditoría A-17):** solo con casos posteriores a su fecha de corte (≥ 2026-07-01) y siempre frente a un **placebo** que veta al azar con la misma tasa. Las tres carteras de la sombra son: A = regla pura, B = regla + veto de Claude, C = regla + veto placebo.

## 5. Hipótesis

| ID | Estado | Documento |
|---|---|---|
| Protocolo común | v1, fusionado en `4614d65`, congelado (confirmado por el propietario el 23-oct-2026) | `research/preregistration/00-protocolo-comun.md` |
| H1 | v1 fusionado: momentum diario en BTC | `H1-momentum-series-temporales-diario.md` |
| H2 | v1 fusionado: ruptura de canal en 4h, BTC + ETH + 8 alts, filtro de expansión | `H2-ruptura-canal-4h.md` |
| H3 | Aplazada a la F9 | `H3-momentum-transversal-alts.md` |
| H4 | v1 fusionado: filtro de funding sobre H1 y H2 | `H4-filtro-funding-oi.md` |
| H5 | Idea: aprendizaje automático, bajo las reglas del ADR-008 | — |
| Aclaraciones | Detalle de implementación fijado antes de cualquier dato | `ACLARACIONES-v1.md` |

**Gate de la F4:** sin cambios respecto al v2 §5; las definiciones operativas están en el protocolo común y en las aclaraciones.

## 6. Presupuesto

Ver `docs/presupuesto.md`: ≈USD 110-117/mes **[estimado]**, con el analista dentro de los créditos de API de Max.

## 7. Roadmap y estado

| Fase | Estado al 24-oct-2026 |
|---|---|
| F0 Alcance y gobernanza | **Cerrada** |
| F1 Plataforma | Pendiente del propietario (`docs/f1-verificacion-plataforma.md`) |
| F2 Fundaciones | En curso: CI, motor de riesgo y auditoría hechos; falta SOPS/age operativo (clave pública del propietario) |
| F3 Datos públicos | En curso: 2020-2024 descargado y verificado (99.88% de completitud, `docs/datos/calidad-f3.md`); falta una segunda fuente independiente |
| F4 Investigación | En curso: 296 corridas sobre 2020-2024 con el holdout sellado; **ninguna hipótesis pasa el gate** (`docs/resultados/f4-analisis.md`) |
| F5 Analista Claude | No empezada |
| F6 Riesgo y ejecución | No empezada (el motor de riesgo v0/v1 ya existe) |
| F7 Sombra | No empezada (≥12 semanas) |
| F8 Piloto real | No empezada (3 meses, USD 1,500) |
| F9 Escala | No empezada |
| Centro de Mando | API y app web hechas, con E2E y Docker (ADR-014, ADR-015); falta el despliegue en el VPS |

Faltantes, horas estimadas y lista del propietario: `docs/estado-y-faltantes.md`.

## 8. Pendientes del propietario

Ver `docs/estado-y-faltantes.md` §3. Resumen: verificaciones de la F1 (Binance, Hyperliquid), reclamar los créditos de API de Max, clave pública `age`, aprobar o ajustar ADR-013 y validar el reporte fiscal con el contador.
