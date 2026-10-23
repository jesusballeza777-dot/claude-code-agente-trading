# F1: verificaciones de plataforma que hace el propietario

**Estado:** pendiente · **Fecha:** 23-oct-2026 · **Fuentes:** plan §1, §3, §8; ADR-001, ADR-002, ADR-003; protocolo común C-14, C-19

Estas comprobaciones solo se pueden hacer desde las cuentas del propietario. Claude no entra en ellas
ni necesita credenciales para nada de esta lista.

> **Nunca** compartas en el chat, en el repositorio ni en ningún documento: claves de API, secretos,
> contraseñas, códigos 2FA ni frases semilla (CLAUDE.md regla 1). Para esta fase basta con contar
> el **resultado** de cada comprobación.

**MetaMask no forma parte del proyecto:** no hay operaciones en cadena, ni puentes, ni DeFi. No hace falta conectarlo a nada.

## 1. Binance (bloqueante para el apalancamiento, plan §8)

| # | Comprobación | Dónde | Qué anotar |
|---|---|---|---|
| 1 | Futuros USDⓈ-M habilitados para tu cuenta en México | App o web → Futuros → USDⓈ-M; completar el cuestionario de derivados si aparece | Habilitado sí/no; si aparece un aviso de restricción por país, su texto |
| 2 | Se puede abrir una posición (opcional pero recomendado) | Una orden mínima en BTCUSDT o BTCUSDC, margen **aislado**, apalancamiento 1×, y cerrarla al momento. Coste ≈ USD 0.10 en comisiones | Si se pudo abrir y cerrar |
| 3 | Comisiones de tu cuenta en futuros | Perfil → Comisiones (Fee rate) → USDⓈ-M | Maker y taker para contratos con margen en USDT y en USDC |
| 4 | Nocional mínimo y paso de cantidad | Futuros → BTCUSDT / ETHUSDT (y USDC) → Información del contrato / Reglas de trading | Nocional mínimo y cantidad mínima de cada uno |
| 5 | Margen en USDC | Futuros → Preferencias → Modo multiactivo; disponibilidad de BTCUSDC/ETHUSDC | Si prefieres operar contratos con margen en USDC o en USDT con USDC como colateral |
| 6 | Cuenta o subcuenta dedicada solo al proyecto | Gestión de subcuentas (si tu cuenta lo permite) | Si existe; si no, usar una cuenta separada |

**No crear claves de API todavía.** Se crean en la F6 con: lectura + trading spot + trading de futuros, **sin retiros**,
con IP whitelist de la IP fija del VPS, y se guardan cifradas con SOPS/age (ver `ops/secrets.md`).

Si el punto 1 falla, la parte apalancada cambia de plataforma (ADR-002: Kraken como contingencia) o el alcance pasa a spot
con un ADR nuevo.

## 2. Claude: Max 5x o Pro + API (plan §8)

- **Por verificar:** hasta donde sé, las suscripciones Pro y Max cubren claude.ai y Claude Code, pero **no incluyen créditos de la API**; la API se paga aparte, por consumo, en la consola de Anthropic. Si es así, el supuesto del plan §6 ("Max 5x con API cubierta por los créditos") no se cumple.
- **Uso estimado de la API por el analista** (F5 en adelante): unas pocas llamadas al día, del orden de USD 5-15/mes con un modelo de gama Opus (**estimado**; se mide en la F5).
- **Recomendación:** Max 5x para desarrollar con Claude Code a 20 h/semana (con Pro es fácil llegar a los límites de uso) **y** una cuenta de API con prepago pequeño para el analista. Presupuesto resultante: ≈USD 120-130/mes en lugar de 110-117.
- Al decidir, se fija el identificador exacto del modelo en ADR-003 tras comprobarlo con `GET /v1/models`.

## 3. Contador (antes de la F8)

- Tratamiento fiscal de los derivados (perpetuos) frente al spot en México.
- Documentación que necesita de cada operación (el registro de auditoría de la F6 se diseña con esa lista).

## Registro de resultados

| # | Resultado | Fecha |
|---|---|---|
| 1.1 | | |
| 1.2 | | |
| 1.3 | | |
| 1.4 | | |
| 1.5 | | |
| 1.6 | | |
| 2 | | |
