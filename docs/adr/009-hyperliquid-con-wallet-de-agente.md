# ADR-009: Hyperliquid como segunda plataforma, con wallet de agente sin retiros

- **Estado:** Aceptado (decisión del propietario del 23-oct-2026)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** CLAUDE.md reglas 1, 5 y 8; ADR-001, ADR-002, ADR-007

## Contexto

- El propietario quiere que el sistema opere también en Hyperliquid (exchange descentralizado de perpetuos) y tiene MetaMask.
- Dar al sistema la frase semilla o la clave privada de MetaMask equivale a darle custodia total, incluidos los retiros: rompe las reglas 1 y 8. Como el sistema va a leer datos externos no confiables (regla 5), una instrucción maliciosa incrustada en una noticia o una web podría intentar aprovechar esa custodia.
- Hyperliquid permite autorizar **wallets de agente** (API wallets) desde la wallet principal: el agente puede firmar órdenes y cancelaciones, pero **no retiros**; un retiro solo lo firma la wallet principal **[confirmado en documentación de terceros; por verificar en la documentación oficial en F1]**.

## Decisión

1. Hyperliquid se añade como **segunda plataforma de perpetuos**, junto a Binance (ADR-002). Kraken sigue como contingencia.
2. Acceso **solo mediante wallet de agente**:
   - El propietario la autoriza una vez desde MetaMask (acción `approveAgent`), con nombre, en su propio dispositivo.
   - La clave del agente se guarda cifrada con SOPS/age (ver `ops/secrets.md`) y solo puede operar.
   - **Nunca** se guarda, se pide ni se registra la frase semilla ni la clave privada de MetaMask. MetaMask no se conecta al sistema.
   - Depósitos y retiros (MetaMask ↔ Hyperliquid) los hace el propietario a mano; ningún código llama a acciones de retiro o transferencia (regla 8).
   - Si la clave del agente se expone: el propietario revoca el agente desde la wallet principal y autoriza otro.
3. **Validación:** los backtests usan datos de Binance (Hyperliquid tiene poco histórico). Hyperliquid se valida en sombra (F7) con sus propios costes, funding (horario) y reglas de liquidación antes de operar con dinero real.
4. **Motor de riesgo:** los límites del plan §3 se aplican a la **cuenta total** (Binance + Hyperliquid), no por plataforma. La estimación de liquidación es específica de cada plataforma: la fórmula actual es la de Binance, y la de Hyperliquid se añade en la F6.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Clave privada o frase semilla de MetaMask en el sistema | Custodia total con capacidad de retiro; rompe las reglas 1 y 8 |
| Firmar cada operación a mano en MetaMask | Incompatible con el nivel A y con operar de madrugada |
| Solo Binance | Rechazado por el propietario |

## Consecuencias

- **Positivas:** sin custodia de fondos por parte del sistema; contraparte diversificada. El mínimo de orden de Hyperliquid (≈USD 10, **por verificar**) es más bajo que el de BTCUSDT en Binance, lo que ayuda con un capital de USD 1,500.
- **Negativas:** riesgo de contrato inteligente, del puente y del oráculo; el capital se reparte entre dos plataformas; el registro fiscal tiene que incluir operaciones en un exchange descentralizado.
- **Por verificar en F1:** que Hyperliquid no restrinja a residentes en México (sus términos excluyen al menos EE. UU., Ontario y países sancionados), comisiones por nivel, mínimo de orden y modo de margen aislado.
