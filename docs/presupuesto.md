# Presupuesto mensual del proyecto

**Fuente única** de las cifras de gasto (auditoría A-13). Los demás documentos apuntan aquí.
**Fecha:** 23-oct-2026 · **Moneda:** USD; MXN al FIX de 18.70 del plan §6 (**por verificar**: el tipo actual no se pudo consultar porque Banxico está bloqueado desde el entorno de desarrollo).

## Escenario vigente

| Concepto | USD/mes | Estado | Notas |
|---|---|---|---|
| Claude Max 5x | 100 | estimado (precio del plan §6) | Desarrollo con Claude Code |
| API de Claude para el analista | 0 dentro de los créditos | **confirmado** que Max 5x incluye USD 100/mes en créditos de API ([centro de ayuda de Claude](https://support.claude.com/en/articles/17154008-api-credits-for-max-and-team-plans)) | Uso estimado del analista: USD 5-15/mes. Los créditos no se acumulan de un mes a otro |
| VPS en la UE y copias de seguridad | 10-17 | estimado | F6 en adelante |
| Datos de mercado (archivo y API pública de Binance) | 0 | confirmado | Sin claves |
| Hyperliquid | 0 | confirmado | Sin suscripción; las comisiones van por operación |
| Tailscale (acceso al Centro de Mando) | 0 | por verificar | Plan personal gratuito |
| GitHub Actions | 0 | por verificar | Depende de si el repositorio es privado y de los minutos gratuitos del plan |
| **Total** | **≈110-117** | estimado | **≈MXN 2,060-2,190**; ≈7.5% mensual del capital de USD 1,500 |

## Escenario alternativo (si no se reclaman los créditos)

Si los créditos de API no se vinculan a la organización de la consola, el analista se paga por consumo: **≈USD 115-132/mes**.

## Cómo reclamar los créditos (lo hace el propietario)

1. Llevar al menos 7 días en el plan Max.
2. En claude.ai: Settings → Billing → "API credits" → **Link organization**, y elegir o crear la organización de la consola.
3. Se puede vincular una sola organización, y después no se puede cambiar.

## Lo que no está en el presupuesto

- Comisiones de trading y funding: van en los resultados de cada operación, no en el gasto fijo.
- Impuestos y honorarios del contador.
- Sin tope de gasto (ADR-008): se recomienda revisar este documento cada mes.
