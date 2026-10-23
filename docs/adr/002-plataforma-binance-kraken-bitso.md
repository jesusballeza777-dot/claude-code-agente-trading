# ADR-002: Plataforma: Binance, Kraken como contingencia, Bitso como rampa MXN

- **Estado:** Propuesto (recoge la decisión del propietario del 22-oct-2026; falta su aprobación de este texto)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §1 (#1, #4), §3, §8; CLAUDE.md reglas 1 y 8

## Contexto

- El propietario ya tiene cuenta en Binance **[confirmado, plan §1 #4]**.
- La operativa requiere spot y perpetuos USDⓈ-M (ADR-001).
- No está confirmado que los futuros USDⓈ-M estén habilitados para su cuenta en México **[PENDIENTE, plan §8]**.
- El propietario opera desde México y necesita convertir MXN a USDC.

## Decisión

1. **Binance** es la plataforma principal: spot y perpetuos USDⓈ-M, en una cuenta (o subcuenta) dedicada solo a este proyecto con USD 1,500 en USDC.
2. **Kraken** es la plataforma de contingencia, para dos casos:
   - Los futuros de Binance no están disponibles para México (resultado de la F1).
   - Binance deja de ser utilizable (restricción regulatoria, caída prolongada, problema de solvencia).
3. **Bitso** es solo la rampa de entrada y salida en MXN (SPEI ↔ USDC). No se opera en Bitso.
4. **Claves API** (plan §3; CLAUDE.md reglas 1 y 8): lectura + trading spot + trading de futuros, **sin permiso de retiro**, con IP whitelist. Los movimientos entre plataformas (Bitso ↔ Binance) los hace el propietario a mano; ningún código llama a endpoints de retiro o transferencia.
5. El código de ejecución (F6) accede al exchange a través de una interfaz propia para que cambiar a la contingencia no toque las capas de señal, decisión ni riesgo.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Kraken como principal | El propietario ya opera en Binance; disponibilidad de derivados para México por verificar |
| Otros exchanges de derivados | Disponibilidad y marco regulatorio para residentes en México sin verificar; más superficie de riesgo de contraparte |
| Solo Bitso | No ofrece perpetuos; no cubre ADR-001 |
| Varias plataformas activas a la vez | Más claves, más superficie de ataque y más complejidad sin beneficio con USD 1,500 |

## Consecuencias

- **Positivas:** cuenta existente; datos de futuros gratuitos en el MVP **[estimado, plan §6]**; una sola contraparte activa.
- **Negativas:** riesgo de contraparte y regulatorio concentrado en Binance; se mitiga manteniendo en Binance solo el capital de trading.
- **Cambio a la contingencia:** cambia comisiones, datos y reglas de liquidación; las estrategias validadas con datos de Binance deben revalidarse antes de operar en Kraken.
- **Por verificar:**
  - F1: futuros USDⓈ-M de Binance habilitados para la cuenta (cuestionario de derivados superado y posibilidad de abrir una posición).
  - F1: disponibilidad de derivados de Kraken para residentes en México.
  - F1: redes y comisiones para mover USDC entre Bitso y Binance.
