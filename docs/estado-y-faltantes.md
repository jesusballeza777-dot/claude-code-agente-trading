# Estado del proyecto y faltantes

- **Fecha:** 24-oct-2026 · **Rama:** `claude/maestro-v2-phase0-foundations-wp6t5d` · **Plan rector:** `docs/plan-maestro-v2.1.md`.
- **Etiquetas:** [confirmado] verificado con tests, datos o salida reproducible; [estimado] cálculo o juicio razonado; [hipótesis] por demostrar; [por verificar] depende de algo que no se puede comprobar desde aquí.
- La app (página Hoy y Proyecto) lee la tabla del §3 de este documento: es la fuente única de tus pendientes.

## 1. Hecho y verificado

| Pieza | Evidencia | Estado |
|---|---|---|
| Gobernanza F0: ADR-001 a 012, plan v2.1, presupuesto, requisitos y riesgos | `docs/adr/README.md`, auditoría en `docs/auditoria/` | [confirmado] |
| CI con lint, tipos, tests, cobertura y gitleaks del historial completo | `.github/workflows/ci.yml` | [confirmado] |
| Motor de riesgo v0 (límites F7-F8 firmados) y reglas v1 propuestas, con explicación en español de cada veto | `src/trading/risk/`; 100% de cobertura de líneas y ramas; ADR-007 y ADR-013 (Propuesto) | [confirmado] |
| F3: datos públicos 2020-2024 sin claves, con SHA-256 por fichero y guardia del holdout | 15,695 ficheros verificados; completitud 99.88% (`docs/datos/calidad-f3.md`); ADR-016 | [confirmado] |
| Universo point-in-time de H2, con contratos deslistados | `docs/datos/universo-h2-v1.md` | [confirmado] |
| Backtester por eventos con el motor de riesgo real, costes y funding | `src/trading/backtest/`; tests sintéticos de look-ahead | [confirmado] |
| F4 sobre 2020-2024: 296 corridas anotadas, holdout sellado | `research/trials.csv`, `research/results/`, `docs/resultados/f4-2020-2024.md` | [confirmado] |
| Veredicto de la F4: ninguna hipótesis pasa el gate (H2-v1 cumple 9 de 10; falla el PBO 0.456) | `docs/resultados/f4-analisis.md` | [confirmado] |
| Centro de Mando: API de solo lectura (scrypt + TOTP, CSP, anti-CSRF) y app web con Brújula | `src/trading/api/`, `app/web/`; ADR-014, ADR-015; test que falla si aparece una ruta de escritura nueva | [confirmado] |
| Reportes PDF, Excel y CSV (semanal, mensual, ficha, contador) con procedencia y cadena de auditoría | `src/trading/reporting/`, ADR-017 | [confirmado] |
| Tests de la app web: Vitest, E2E con Playwright y accesibilidad con axe en tema claro y oscuro | `app/web/src/**/*.test.ts*`, `app/web/e2e/` | [confirmado] |
| Capturas reproducibles (oscuro, claro y móvil de las 10 páginas) | `docs/capturas/`; `CAPTURAS=1 npx playwright test e2e/capturas.spec.ts` | [confirmado] |
| `docker compose up --build`: base, backend y app en `127.0.0.1:8080` | Probado en el entorno de desarrollo salvo la capa de Pango (ver §6); el job `docker` de CI lo construye completo | [confirmado] en parte |
| App Android (esqueleto con datos de demo) | Compila y pasa tests en CI (ADR-010) | [confirmado] |

## 2. Qué falta, por fase

Horas de trabajo de Claude salvo que se diga otra cosa. Son [estimado]: sirven para ordenar, no son un compromiso.

| Fase | Qué falta | Horas |
|---|---|---|
| F1 Plataforma | Tus verificaciones en Binance, Hyperliquid y Anthropic (§3) | 2-3 h tuyas |
| F2 Fundaciones | SOPS/age operativo cuando compartas tu clave pública; pasar a las reglas del ADR-013 si lo apruebas | 3-5 h |
| F3 Datos | Segunda fuente independiente para contrastar precios; actualización incremental diaria; carga de TimescaleDB en el VPS | 8-12 h |
| F4 Investigación | Pre-registrar las hipótesis siguientes (ver §4), correrlas y documentarlas | 15-25 h + 2 h tuyas de revisión |
| F5 Analista Claude | Prompts con datos no confiables aislados, validación JSON, registro de decisiones y evaluación sin dinero | 30-40 h |
| F6 Riesgo y ejecución | Módulo de ejecución (testnet primero), parada de emergencia, calendario macro y precio de stablecoins para el ADR-013, alertas | 60-80 h |
| F7 Sombra | Operar en papel ≥12 semanas con el sistema completo; la sombra es el juez de cualquier hipótesis nueva | 20 h de puesta en marcha + seguimiento; ≥12 semanas de calendario |
| F8 Piloto real | 3 meses con USD 1,500; requiere tu CLI con TOTP y commit firmado para `LIVE_TRADING` | Decisión tuya; sin estimación |
| F9 Escala | Solo si la F8 lo justifica | Sin estimación |
| Centro de Mando | Despliegue en el VPS con Tailscale; cliente Android ligero sobre la API (ADR-014); historial de vetos con "qué habría pasado" (F7) | 15-20 h |

## 3. Tus pendientes, en orden

Ninguno se puede hacer desde la app ni desde esta sesión: necesitan tus cuentas, tus claves o tu firma.

| # | Pendiente | Documento |
|---|---|---|
| 1 | Verificar en Binance que tu cuenta permite futuros USDⓈ-M, comisiones y nocional mínimo | docs/f1-verificacion-plataforma.md |
| 2 | Generar tu clave age y compartir solo la pública para SOPS | ops/secrets.md |
| 3 | Aprobar o ajustar el ADR-013 (reglas de riesgo más restrictivas) | docs/adr/013-motor-de-riesgo-v1-reglas-ampliadas.md |
| 4 | Reclamar los créditos de API de Max 5x en la consola | docs/presupuesto.md |
| 5 | Revisar los resultados de la F4 y decidir los siguientes pre-registros | docs/resultados/f4-analisis.md |
| 6 | Validar el formato del reporte fiscal con tu contador | docs/app/especificacion.md |
| 7 | Cuando haya VPS: crear las credenciales del Centro de Mando en tu ordenador | README.md |

## 4. Decisiones abiertas y recomendación

| Decisión | Opciones | Recomendación |
|---|---|---|
| Qué hacer tras la F4 | A cerrar H1-H4 como negativo · B pre-registrar H2-v2 · C protocolo v2 del PBO · D abrir el holdout | **B + C**: H2-v2 pre-registrada (por ejemplo solo largos) con la sombra como juez principal y el holdout reservado; protocolo v2 del PBO explicado antes de correr nada. **D no**: H2-v1 no pasa los criterios 1-8 |
| ADR-013 | Aprobar tal cual · ajustar · rechazar | Aprobar: en la sensibilidad de H2 casi no cambia el resultado (+0.509 R frente a +0.516 R) y añade protecciones (funding en contra, máximo de posiciones, depeg, ventanas macro) |
| H1 con nocional mínimo real | Esperar a la F1 · pre-registrar H1-v2 | Esperar a la F1: si el mínimo real es menor, H1-v2 tendría muestra; contaría en el N del DSR |
| Despliegue del Centro de Mando | Solo local · VPS con Tailscale | VPS con Tailscale cuando exista el VPS; nunca publicado en internet |

## 5. Riesgos abiertos

| Riesgo | Por qué importa | Mitigación |
|---|---|---|
| Sobreajuste | H2-v1 falla el PBO; cualquier ajuste mirando resultados contamina la evidencia | Pre-registro antes de correr; todo intento cuenta en `trials.csv` y en el N del DSR |
| Sesgo de régimen | 2020-2024 fue muy alcista (BTC de USD 7,201 a USD 93,576); los cortos de H2 pierden (−0.081 R) | Juzgar en sombra y, una sola vez, en el holdout |
| Ninguna estrategia con evidencia | Sin estrategia aprobada no hay camino a la F7 | Seguir el §4; no relajar el gate |
| Una sola fuente de datos | Un error del archivo de Binance pasaría desapercibido | Segunda fuente independiente (F3) |
| Límites v1 sin aprobar | Los backtests usan F7-F8 (firmados); el ADR-013 es Propuesto | Tu decisión del §3 punto 3 |
| Seguridad del Centro de Mando en un VPS real | La autenticación se probó en tests y en Docker local, no en un VPS | Checklist de despliegue (README) y Tailscale; nunca puerto público |
| Créditos de API sin reclamar | El presupuesto asume el analista dentro de los créditos de Max | §3 punto 4 |

## 6. Por verificar

| Qué | Por qué no se pudo verificar aquí | Cómo se verifica |
|---|---|---|
| Capa de Pango de la imagen del backend (PDF dentro de Docker) | La red de la sesión bloquea `deb.debian.org` | Job `docker` de CI: construye la imagen y descarga un PDF por nginx |
| `tailscale serve` y el arranque con `sops exec-env` en el VPS | No hay VPS ni Tailscale en esta sesión | Primer despliegue, siguiendo el README |
| Nocional mínimo, comisiones y apalancamiento reales en Binance | Necesita tu cuenta | F1 (§3 punto 1) |
| Fórmula de liquidación de Hyperliquid | La fórmula implementada no se ha contrastado con el exchange | F1 y testnet en la F6; mientras, el motor veta si falta el modelo |
| Segunda fuente independiente de precios | Pendiente de elegir y de comprobar su licencia | F3 |
| Tipo de cambio FIX de Banxico para el reporte fiscal | El reporte usa un tipo del plan y lo marca como pendiente | Tu contador (§3 punto 6) |
| Fuentes del calendario macro y del precio USD de las stablecoins | Las reglas del ADR-013 las necesitan en vivo | F6 |

## 7. Siguiente paso

1. Tú: los puntos 1 a 5 del §3 (empezando por la F1 y el ADR-013).
2. Claude, en cuanto decidas el §4: redactar el pre-registro de H2-v2 y el protocolo v2 del PBO, fusionarlos y solo entonces correr nada.
3. En paralelo y sin claves: segunda fuente de datos (F3) y despliegue del Centro de Mando en el VPS cuando exista.
