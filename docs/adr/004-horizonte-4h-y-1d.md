# ADR-004: Horizonte: velas de 4h y 1d

- **Estado:** Aceptado (aprobado por el propietario el 23-oct-2026)
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** plan maestro v2 §1 (#3, #5), §3, §4, §5

## Contexto

- Las hipótesis prioritarias son H1 (momentum diario) y H2 (ruptura de canal en 4h) **[confirmado, plan §5]**.
- El nivel B requiere la aprobación manual de cada señal por Telegram **[confirmado, plan §4]** y el propietario dedica 20 h/semana **[confirmado, plan §1]**.
- Comisiones y funding se pagan sobre el nocional **[confirmado, plan §3]**: cuanto más corto el horizonte, más pesan los costes frente al movimiento esperado.
- El gate de la F4 exige ≥200 operaciones fuera de muestra **[confirmado, plan §5]**: un horizonte demasiado largo no genera muestra suficiente.

## Decisión

1. Las señales se calculan **solo sobre velas cerradas de 4h y 1d**, con límites de vela en UTC (4h: 00, 04, 08, 12, 16 y 20 UTC; 1d: 00:00 UTC).
2. No hay señales intra-vela. La entrada se produce después del cierre de la vela que genera la señal.
3. El riesgo intra-vela lo cubre el stop STOP_MARKET reduce-only colocado en el exchange desde la entrada (ADR-001).
4. Cualquier horizonte más corto requiere un ADR nuevo.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| 1h o menos | Los costes sobre el nocional pesan más; más ruido; aprobación manual inviable con 20 h/semana |
| Semanal | Muy pocas operaciones para el gate de ≥200 fuera de muestra |
| Solo 1d | Muestra más pequeña; deja fuera H2 |
| Solo 4h | Deja fuera H1, cuya referencia académica es de horizonte diario/semanal |

## Consecuencias

- **Positivas:** pocos puntos de decisión al día (máximo 6 por símbolo en 4h); costes más pequeños en relación con el movimiento esperado.
- **Negativas:** las velas de 4h cierran a las 18, 22, 02, 06, 10 y 14 h del centro de México (UTC−6); las señales de madrugada esperan la aprobación del nivel B. Hay que definir una **ventana de validez de la señal** (PENDIENTE, F6): pasada esa ventana sin aprobación, la señal caduca.
- El funding se liquida cada 8h; las posiciones de varias velas pagan o cobran funding, que el backtest debe incluir.
- El riesgo de muestra pequeña es mayor en 1d (ver `docs/risk_register.md`).
