# F1: verificaciones de plataforma que hace el propietario

**Estado:** pendiente · **Fecha:** 23-oct-2026 · **Fuentes:** plan §1, §3, §8; ADR-001, ADR-002, ADR-003; protocolo común C-14, C-19

Estas comprobaciones solo se pueden hacer desde las cuentas del propietario. Claude no entra en ellas
ni necesita credenciales para nada de esta lista.

> **Nunca** compartas en el chat, en el repositorio ni en ningún documento: claves de API, secretos,
> contraseñas, códigos 2FA ni frases semilla (CLAUDE.md regla 1). Para esta fase basta con contar
> el **resultado** de cada comprobación.

**MetaMask solo se usa para autorizar la wallet de agente de Hyperliquid** (ADR-009), desde tu propio dispositivo. El sistema nunca recibe tu frase semilla ni tu clave privada.

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

## 2. Hyperliquid (ADR-009)

| # | Comprobación | Dónde | Qué anotar |
|---|---|---|---|
| 1 | Que los términos de uso no restringen a residentes en México | app.hyperliquid.xyz → Terms (sección de personas restringidas) | Restringido sí/no |
| 2 | Comisiones de tu nivel y mínimo de orden | Documentación de Hyperliquid → Fees / Trading | Maker, taker y mínimo de orden en USD |
| 3 | Margen aislado disponible en BTC y ETH | Al abrir una orden, selector Cross / Isolated | Sí/no |

**No autorices todavía la wallet de agente.** Se hace en la F6, cuando el backend esté listo para guardarla cifrada.
Al autorizarla: un nombre fijo (por ejemplo `trading-agente`), desde MetaMask en tu dispositivo, y anotar solo la **dirección pública** del agente.

## 3. Claude: cuenta de API para el analista (ADR-003)

- **Decidido el 23-oct-2026:** Max 5x para desarrollar y una cuenta de API por consumo para el analista.
- Crear la cuenta en la consola de Anthropic con un prepago pequeño y un límite de gasto mensual (por ejemplo, USD 30).
- La clave de API **no** se comparte en el chat: se guarda cifrada con SOPS/age en la F5 (`ops/secrets.md`).
- Con la cuenta creada se comprueba el identificador exacto del modelo con `GET /v1/models` y se fija en ADR-003.

## 4. Contador (antes de la F8)

- Tratamiento fiscal de los derivados (perpetuos) frente al spot en México, y de las operaciones en un exchange descentralizado (Hyperliquid).
- Tipo de cambio para convertir a MXN (FIX de Banxico) y fecha de referencia (cierre de la operación en hora de CDMX); el reporte de la app los usa (ver `docs/app/especificacion.md`).
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
| 2.1 | | |
| 2.2 | | |
| 2.3 | | |
| 3 | | |
