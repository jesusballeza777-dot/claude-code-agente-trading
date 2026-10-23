# Runbook operativo

**Estado:** esqueleto (F0). No hay nada desplegado ni conectado a exchanges.

## Invariantes que este runbook nunca relaja

- `LIVE_TRADING=false`. Solo el propietario puede activarlo, por CLI local con TOTP y commit firmado (CLAUDE.md, regla 2). El mecanismo se construye en la F6.
- Las claves de exchange no tienen permiso de retiro y usan IP whitelist (plan §3).
- El motor de riesgo tiene veto absoluto; un error en cualquier punto del flujo equivale a "no operar".

## Procedimientos (por completar)

| Procedimiento | Fase en que se define |
|---|---|
| Arranque y parada del sistema | F6 |
| Kill switch y cierre de todas las posiciones | F6 |
| Rotación de claves (SOPS/age) | F2 |
| Respuesta a fuga de secretos (alerta de gitleaks) | F2 |
| Caída de datos o datos atrasados | F3 |
| Caída o restricción del exchange (contingencia Kraken, ADR-002) | F6 |

## Incidentes

Cada incidente se documenta en `ops/incidents/AAAA-MM-DD-titulo.md` con: cronología (UTC), impacto, causa raíz, acciones y seguimiento.
