# ADR-012: Estado de fases y arranque de la F3 con datos públicos

- **Estado:** Aceptado (instrucción del propietario en el prompt v3, 23-oct-2026)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** ADR-005; CLAUDE.md; plan maestro v2.1 §7; auditoría A-15

## Contexto

CLAUDE.md fijaba como fase actual "F0 cerrada; F1 + cimientos de F2" y prohibía escribir código que se conecte a Binance "hasta la F1/F3". La F1 depende de comprobaciones que solo puede hacer el propietario en sus cuentas, y no bloquea la descarga de datos públicos, que no necesita cuenta ni claves.

## Decisión

1. **F0 cerrada.** **F1 pendiente del propietario.** **F2** (fundaciones) **y F3** (datos), así como el **Centro de Mando**, quedan en curso en paralelo.
2. La F3 arranca **solo con datos públicos**: el archivo `data.binance.vision`, sin claves y sin endpoints de cuenta, órdenes, retiro ni transferencia. El test de gobernanza que prohíbe esos endpoints se amplía para cubrir el código de datos.
3. La F4 (backtests) puede usar estos datos sobre 2020-2024. El holdout sigue sellado, también en código (`trading.data.holdout`).
4. CLAUDE.md y el README apuntan al plan v2.1.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Esperar a la F1 para empezar la F3 | La F1 no aporta nada a la descarga de datos públicos; solo retrasaría el proyecto |
| Usar la API pública de Binance | Bloqueada desde el entorno de desarrollo; el archivo cubre lo necesario y trae checksums |

## Consecuencias

- Se puede investigar mientras el propietario hace la F1.
- Si la F1 cambia de plataforma (ADR-002, contingencia), los datos de Binance siguen sirviendo para investigar, pero la ejecución y los costes deben revalidarse.
