# Pre-registro H3: momentum transversal en alts líquidas, neutral al mercado

- **ID:** H3 · **Versión:** v0 · **Prioridad:** Baja (plan §5)
- **Estado:** APLAZADO hasta la F9 (decisión H3-07, tomada el 23-oct-2026 por delegación del propietario)
- **Fecha:** 2026-10-23

## Por qué se aplaza

1. **Prioridad baja** en el plan, con 20 h/semana para todo el proyecto: las horas rinden más en H1, H2 y H4.
2. **Encaje con el motor de riesgo:** una cartera neutral de 6-10 patas no tiene un "stop de la operación" natural. Dimensionarla requiere definir el riesgo a nivel de cartera, lo que es un cambio del motor de riesgo y necesita un ADR.
3. **Capital:** con USD 1,500 y apalancamiento efectivo ≤2×, cada pata tendría unos USD 300 y los costes de rotación semanal pesarían mucho frente a la ventaja esperada.

No se ha ejecutado ningún backtest de H3. Al retomarla se redacta **H3-v1** desde la plantilla, con las preguntas H3-01 a H3-08 de la v0 como punto de partida, y cuenta como una especificación más en el DSR (C-11).

## Contenido de la v0 (referencia)

- **Hipótesis:** entre las alts líquidas, las que más han subido en las últimas semanas siguen rindiendo más que las que más han caído; una cartera larga en las más fuertes y corta en las más débiles tiene esperanza neta positiva.
- **Referencia candidata [por verificar]:** Liu, Tsyvinski y Wu, "Common Risk Factors in Cryptocurrency", *Journal of Finance* (2022).
- **Preguntas que quedan abiertas para la H3-v1:** universo (H3-01), señal de ranking (H3-02), construcción y neutralidad (H3-03), rebalanceo (H3-04), stops y riesgo de cartera (H3-05), qué cuenta como operación (H3-06), límite de apalancamiento compartido (H3-08).

## Registro de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| v0 | 2026-10-23 | Borrador con decisiones abiertas |
| v0 | 2026-10-23 | Aplazada hasta la F9 (H3-07) |
