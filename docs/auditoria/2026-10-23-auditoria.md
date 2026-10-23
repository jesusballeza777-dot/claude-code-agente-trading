# Auditoría del repositorio: 23-oct-2026

- **Alcance:** código (`src/trading/`), tests, pre-registro, documentos de gobernanza (plan, requisitos, ADR-001 a 011, registro de riesgos), seguridad y CI. Commit de partida: `122a53b` (línea base en `2026-10-23-linea-base.md`).
- **Método:** lectura completa de los documentos rectores y del código, verificación de los hallazgos externos del prompt v3 (§2) contra el repositorio, y comprobaciones directas (archivo público de Binance, centro de ayuda de Claude).
- **Severidad:** crítica (puede causar pérdida de dinero o invalidar la evidencia), alta (debe resolverse antes de la fase que lo usa), media (inconsistencia o hueco con impacto acotado), baja (calidad o documentación).
- **Estado:** `corregido` (en esta sesión, con commit), `propuesto` (requiere aprobación del propietario; ADR en estado Propuesto), `planificado` (fase futura, en `docs/estado-y-faltantes.md`), `descartado` (el hallazgo externo no se sostiene).

## 1. Verificación de los hallazgos externos (prompt v3, §2)

| Hallazgo externo | Veredicto | Comentario |
|---|---|---|
| 2.1 Plan v2 §8 desactualizado | **Correcto** | `docs/plan-maestro-v2.md:117-125` sigue con casillas sin marcar ya resueltas por ADR-007, ADR-008 y requisitos §7 |
| 2.1 Fase actual en CLAUDE.md | **Correcto en parte** | `CLAUDE.md:19` ya decía "F0 cerrada; F1 + F2", pero no recogía F3 ni la app |
| 2.1 Max no incluye créditos de API | **Correcto: el error era nuestro** | Verificado en [support.claude.com, art. 17154008](https://support.claude.com/en/articles/17154008-api-credits-for-max-and-team-plans): Max 5x recibe USD 100/mes en créditos de API. `docs/adr/003-modelos-claude-version-fijada.md:12` afirmaba lo contrario |
| 2.1 Presupuesto incoherente | **Correcto** | USD 110-117 (plan §6) frente a 120-130 (`docs/requirements.md:120`, `docs/risk_register.md:60`, `docs/adr/008-…:39`) |
| 2.2 Huecos del motor de riesgo | **Correcto** | `limits_f7_f8.toml` solo tiene `[risk]`, `[exposure]` y `[data_freshness]`; nada de beta, alts, depeg, eventos, circuit breakers ni liquidez |
| 2.3 Guardia del holdout solo en documentos | **Correcto** | Regla 7 de CLAUDE.md sin código que la haga cumplir |
| 2.3 Registro de pruebas no obligatorio | **Correcto** | `research/trials.csv` solo tiene cabecera; nada obliga a escribirlo |
| 2.3 Supervivencia en H2 | **Verificado: el archivo conserva deslistados** | LUNAUSDT (2021-01 → 2022-05), ANCUSDT (2022-03 → 2022-05), TOMOUSDT (→ 2024-05) siguen en el archivo; 1,056 símbolos de USDⓈ-M, 900 con margen en USDT |
| 2.3 Fecha de corte de Claude | **Correcto** | Ningún documento limitaba la evaluación del analista a casos posteriores a su fecha de corte |
| 2.4 Faltantes estructurales | **Correcto** | Sin capa de datos, backtester, auditoría encadenada, alertas ni sombra |

## 2. Hallazgos

| ID | Área | Sev. | Evidencia | Impacto | Corrección | Estado |
|---|---|---|---|---|---|---|
| A-01 | Metodología | **crítica** | CLAUDE.md regla 7; ningún módulo bloquea fechas ≥2025-01-01 | Un backtest podría leer el holdout por error y quemarlo | Guardia en código (`trading.data.holdout`) que rechaza fechas ≥2025-01-01 sin `research/holdout_unlock.toml` firmado; test que lo demuestra | corregido (Ola 5) |
| A-02 | Metodología | **alta** | `research/trials.csv` vacío; CLAUDE.md regla 6 | Pruebas sin anotar inflarían el DSR real sin que se note | El backtester escribe cada corrida en `trials.csv` (append-only, con hash del pre-registro, dataset y parámetros) y falla si no puede | corregido (Ola 6) |
| A-03 | Pre-registro | **alta** | `H2-ruptura-canal-4h.md:25` ("stablecoins, contratos de índices y activos tokenizados" sin lista) | Elegir la lista después de ver resultados cambiaría el universo. Trampa concreta: `TUSDT` y `BUSDT` no son stablecoins (tokens T y B) | Aclaraciones de implementación con listas exactas por activo base, fijadas **antes** de cualquier backtest real (`research/preregistration/ACLARACIONES-v1.md`) | corregido |
| A-04 | Pre-registro | **alta** | `00-protocolo-comun.md:71-72` (C-10, C-11) | No define la unidad temporal del CSCV ni las entradas del DSR (varianza entre pruebas, curtosis); se podrían elegir a posteriori | Fijadas en `ACLARACIONES-v1.md` antes de ejecutar | corregido |
| A-05 | Riesgo | **alta** | `limits_f7_f8.toml:15-17`; R13 del registro | H2 opera hasta 10 activos muy correlacionados con BTC; el grupo BTC+ETH no limita la exposición agregada a cripto | Reglas nuevas de exposición beta-ajustada, por alt y total en alts, y máximo de posiciones (ADR-013, Propuesto) | propuesto (activo en simulación) |
| A-06 | Riesgo | media | Protocolo C-19 frente a `engine.py:132` | El motor no veta órdenes por debajo del nocional mínimo; solo el backtest lo aplicaría | Veto `BELOW_MIN_NOTIONAL` en el motor (más restrictivo) | corregido (Ola 2) |
| A-07 | Riesgo | media | ADR-001 punto 6: umbral de funding PENDIENTE | Sin protección de coste ante funding extremo en contra | Umbral propuesto con justificación (ADR-013) | propuesto |
| A-08 | Riesgo | media | `liquidation.py:1-10`; ADR-009 punto 4 | La fórmula de liquidación es la de Binance; con Hyperliquid daría un precio incorrecto | El motor exige declarar el modelo de liquidación por plataforma y veta si no hay uno implementado (fallo cerrado) | corregido (Ola 2) |
| A-09 | Riesgo | baja | `models.py:152` (`AccountState`) | El inicio de día y de semana (UTC) lo calcula quien llama; un error ahí cambia los límites | Funciones `day_start` y `week_start` en el motor, con tests de los bordes | corregido (Ola 2) |
| A-10 | Riesgo | media | No existen reglas de depeg, eventos macro, circuit breakers ni liquidez | Entradas en condiciones anómalas (depeg de USDC, FOMC, picos de volatilidad, libros finos) | Reglas nuevas con sus datos como entrada (ADR-013) | propuesto (activo en simulación) |
| A-11 | Producto | media | Los vetos traen un texto técnico (`engine.py`) | La app no puede explicar un veto en lenguaje claro | Función de explicación: código estable más mensaje en español con cifras | corregido (Ola 2) |
| A-12 | Documentación | media | `docs/adr/003-…:12` | Afirmación falsa sobre los créditos de API de Max | Nota de corrección en ADR-003; presupuesto unificado | corregido |
| A-13 | Documentación | media | `requirements.md:120`, `risk_register.md:60`, `adr/008-…:39`, plan §6 | Cuatro cifras de gasto distintas | `docs/presupuesto.md` como única fuente; los demás documentos apuntan a ella | corregido |
| A-14 | Documentación | baja | `plan-maestro-v2.md:117-125` | El plan rector muestra como abierto lo que ya está decidido | `docs/plan-maestro-v2.1.md` (v2 queda como histórico); CLAUDE.md y README apuntan a v2.1 | corregido |
| A-15 | Gobernanza | baja | `CLAUDE.md:19` | La fase actual no recoge F3 ni la app | ADR-012 (estado de fases) y CLAUDE.md actualizado | corregido |
| A-16 | Gobernanza | media | ADR-010 (Android nativo) frente al prompt v3 (Centro de Mando web) | Dos direcciones de producto incompatibles | El propietario eligió web principal + Android como cliente ligero (23-oct-2026); ADR-014 sustituye en parte a ADR-010 | corregido |
| A-17 | Metodología | media | ADR-003 sin regla de evaluación | Evaluar al analista con casos anteriores a su fecha de corte (jun-2026) mide memoria, no criterio | Regla: solo casos ≥2026-07-01 y comparación contra un placebo de vetos aleatorios con la misma tasa (plan v2.1, ADR-003) | corregido (documental; se aplica en F5) |
| A-18 | Auditoría | media | `trading.audit` solo tiene registros en memoria | Un registro modificable no sirve como evidencia ni para el contador | Registro append-only con hash encadenado y verificación | corregido (Ola 4) |
| A-19 | Seguridad | baja | `.github/workflows/ci.yml` sin `pip-audit` ni `npm audit` | Dependencias con vulnerabilidades conocidas pasarían sin aviso | Jobs de auditoría de dependencias | corregido (Ola 7) |
| A-20 | Seguridad | baja | `app/android/gradle/wrapper/gradle-wrapper.properties` sin `distributionSha256Sum` | Integridad de la distribución de Gradle solo por HTTPS | El JAR del wrapper ya se valida en CI; añadir el checksum cuando se pueda leer `services.gradle.org` | planificado |
| A-21 | Datos | media | Formato del archivo de Binance | Las velas spot no tienen cabecera, las de futuros recientes sí; el spot pasa a microsegundos en 2025 | El lector detecta cabecera y unidad de tiempo; tests con ambos formatos | corregido (Ola 5) |
| A-22 | Fiscal | baja | `reporting/tax.py` (convención de tipo de cambio) | El FIX de Banxico se publica en el DOF al día siguiente; la convención "último publicado en o antes" puede no ser la que pide el contador | Se mantiene "por validar con el contador"; Banxico SIE no es accesible desde aquí y su API requiere token | planificado |

## 3. Revisión del motor de riesgo v0 (sin hallazgos de corrección)

Se revisó a mano y se contrastó con los tests:

- **Liquidación en margen aislado:** la fórmula `LP = (WB + cum − s·Q·EP) / (Q·MMR − s·Q)` coincide con la publicada por Binance para una posición aislada en modo one-way. El largo totalmente colateralizado devuelve `None` (no liquidable), y la posición liquidada al abrir da distancia negativa y se veta. **Por verificar en F6:** contra la calculadora del exchange y con los tramos de margen reales.
- **Redondeos:** el tamaño se calcula con redondeo hacia abajo y las comparaciones del motor se hacen sin dividir, con un contexto decimal propio (34 dígitos). Hay un test de regresión que demuestra que el resultado no depende de la precisión global del proceso.
- **Límites exactos y cortos:** cubiertos a ambos lados del límite, tanto en largos como en cortos.
- **Capital a mercado y periodos:** el motor usa el capital a mercado y el máximo histórico. Los inicios de día y de semana los aporta quien llama (ver A-09).

## 4. Seguridad

- Secretos: `gitleaks` en pre-commit y en CI (historial completo); `.gitignore` cubre `.env`, `*.key`, `keys.txt`, `secrets/*` (salvo `*.sops.yaml`), `*.jks` y `*.keystore`. Nada sospechoso en el historial (8+ commits escaneados en cada CI).
- CI: `permissions: contents: read`, acciones fijadas por SHA, `persist-credentials: false`, lockfile obligatorio (`uv sync --locked`) y validación del wrapper de Gradle.
- Gobernanza en código: `LIVE_TRADING` es una constante en `False`, con tests que comprueban que no se activa por entorno y que no hay endpoints de retiro ni de transferencia.
- Pendientes: A-19 y A-20.

## 5. Coherencia plan ↔ requisitos ↔ ADR ↔ código

- Plan v2 desactualizado (A-14); requisitos y ADR al día salvo en presupuesto (A-13) y créditos de API (A-12).
- Los límites del código (`limits_f7_f8.toml`) coinciden con el plan §3 y ADR-007; un test lo comprueba (`tests/risk/test_limits.py`).
- El protocolo común C-19 (nocional mínimo) no estaba en el motor (A-06).
