# ADR-005: Numeración de fases F0-F9

- **Estado:** Aceptado (aprobado por el propietario el 23-oct-2026)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §5, §7, §8; CLAUDE.md

## Contexto

El plan v1 y el v2 organizan el proyecto en fases F0-F9 **[confirmado, plan §7]**. Las reglas de CLAUDE.md, los ADR y el pre-registro se refieren a ellas por número (por ejemplo, "no conectar a Binance hasta la F1/F3", "gate de la F4"). Hace falta una numeración estable y criterios de salida verificables.

## Decisión

La numeración es fija. No se renumera ni se insertan fases intermedias; el trabajo nuevo se asigna a una fase existente o se decide con un ADR.

| Fase | Nombre | Duración aprox. (20 h/sem) | Criterio de salida |
|---|---|---|---|
| F0 | Alcance y gobernanza | 1 sem | Pendientes del plan §8 cerrados: topes de parada decididos (rechazados por el propietario, ADR-008), requisitos v2, ADR-001 a 008 aprobados, pre-registro fusionado con hash de commit, límites de riesgo firmados (ADR-007). **Cerrada el 23-oct-2026** |
| F1 | Plataforma | 1 sem | Futuros USDⓈ-M verificados para México (o contingencia decidida); Max 5x vs Pro + API decidido; identificador del modelo fijado (ADR-003) |
| F2 | Fundaciones de ingeniería y seguridad | 1-2 sem | CI en verde con lint, tipos, tests y gitleaks; SOPS/age operativo; motor de riesgo con cobertura ≥95% |
| F3 | Datos: spot + futuros, funding y OI | 2 sem | Datos históricos y su calidad verificados; holdout 2025-01-01 → hoy sellado |
| F4 | Investigación cuantitativa | 4-5 sem | Gate de la F4 (plan §5) superado por al menos una hipótesis, o hipótesis descartadas |
| F5 | Analista Claude (se solapa con F4) | 2 sem | Decisiones JSON validadas sobre un conjunto fijo de casos; salida inválida → `ABSTAIN` |
| F6 | Riesgo y ejecución, incluidos perpetuos | 2 sem | Ejecución con stop reduce-only, margen aislado y veto del motor de riesgo probados contra el entorno de pruebas del exchange |
| F7 | Shadow trading | ≥12 sem | Resultados en sombra coherentes con el backtest; certificación (o no) de setups de nivel A |
| F8 | Piloto real con USD 1,500 | 3 meses | Revisión con datos reales; fiscalidad revisada con el contador antes de empezar |
| F9 | Escala | Trimestral | Cada aumento de riesgo o apalancamiento con ADR y evidencia |

Los criterios de salida de F1-F3 y F5-F9 que no figuran literalmente en el plan son **propuestos** y requieren aprobación.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Sprints por fecha | No expresan los gates de evidencia (F4, F7) que condicionan el avance |
| Renumerar respecto a v1 | Rompe las referencias existentes en el plan y en CLAUDE.md |

## Consecuencias

- Las referencias a fases en documentos, commits y código son inequívocas.
- La F5 se solapa con la F4; el analista no se evalúa sobre el holdout.
- El propietario rechazó los topes de parada del proyecto (plan §8); ver ADR-008.
