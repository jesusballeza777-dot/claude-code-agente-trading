# ADR-001: Mercado: spot + perpetuos USDⓈ-M

- **Estado:** Aceptado (aprobado por el propietario el 23-oct-2026)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §1 (#2, #4), §2, §3, §8

## Contexto

- En v1 el mercado era spot 1×, solo en largo **[confirmado, plan §2]**.
- El propietario quiere apalancamiento como objetivo del proyecto **[confirmado, plan §1 #2]**.
- Operar en ambas direcciones casi duplica el número de señales y alivia el problema de muestra estadística (gate de la F4: ≥200 operaciones fuera de muestra) **[estimado, plan §2]**.
- El apalancamiento no crea ventaja: multiplica la que haya, y las comisiones y el funding se pagan sobre el tamaño total de la posición **[confirmado, plan §3]**.
- No está confirmado que los futuros USDⓈ-M estén habilitados para la cuenta del propietario en México **[PENDIENTE, plan §8]**.
- El capital está en USDC **[confirmado, plan §1 #1]**. En Binance, "USDⓈ-M" agrupa contratos con margen en USDT y en USDC; cuáles se usan cambia comisiones, liquidez e histórico disponible **[por verificar, F1]**.

## Decisión

1. **Mercados:** Binance spot y perpetuos USDⓈ-M, con largos y cortos.
2. **Apalancamiento:** se deriva del tamaño por riesgo (riesgo fijo por operación / distancia al stop), nunca como objetivo. Topes de apalancamiento efectivo (posición total / capital): 2× en F7-F8 y 3× en F9, este último con ADR y evidencia. Techo del plan: 3×; superarlo requiere un ADR nuevo con evidencia de la F9.
3. **Margen:** siempre aislado, nunca cruzado.
4. **Liquidación:** distancia a liquidación ≥3 veces la distancia al stop.
5. **Stop:** STOP_MARKET reduce-only en el exchange desde la entrada.
6. **Funding:** sin entradas si el funding en contra supera un umbral (valor **PENDIENTE**); el funding se incluye en todos los backtests.
7. **Cortos:** solo en estrategias validadas en ambas direcciones.
8. **Spot:** sin cortos ni margen en spot; las posiciones cortas solo existen en perpetuos.

Los límites numéricos están en el plan §3 y se codifican en `src/trading/risk/` (ver ADR-007).

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Solo spot 1× (v1) | Sin cortos: la mitad de señales y muestra más pequeña; no cumple el objetivo de apalancamiento del propietario |
| Futuros COIN-M | El colateral en cripto añade una exposición direccional no deseada al margen |
| Margen spot | Intereses de préstamo y riesgo de liquidación con menos herramientas (sin stop reduce-only nativo de futuros) |
| Opciones | Complejidad, liquidez y datos fuera del alcance de un capital de USD 1,500 |
| Futuros con vencimiento | Menos liquidez que los perpetuos y gestión de vencimientos |

## Consecuencias

- **Positivas:** más señales por estrategia (largo y corto); cobertura del objetivo de apalancamiento con un tope explícito.
- **Negativas:** riesgo de liquidación; coste de funding cada 8h; comisiones sobre el nocional; backtests más complejos (funding, comisiones de futuros, liquidación).
- **Riesgo de cola:** el 12-mar-2020 BTC cayó cerca de un 40% en un día **[confirmado, plan §3]**; el motor de riesgo tiene que asumir gaps que saltan el stop.
- **Fiscal:** el tratamiento de los derivados es distinto al del spot; se revisa con el contador antes de la F8.
- **Pendiente / por verificar en F1:**
  - Futuros USDⓈ-M habilitados para la cuenta en México. Si no lo están, la parte de apalancamiento cambia de plataforma (ADR-002).
  - Contratos con margen en USDC o en USDT (con USDC como colateral en modo multiactivo): comisiones, liquidez, histórico y efecto sobre la liquidación.
  - Umbral de funding en contra que bloquea entradas.
