# ADR-015: Seguridad del Centro de Mando

- **Estado:** Aceptado. Aplica los principios no negociables del prompt v3 §4.1 y las reglas 1, 2 y 8 de CLAUDE.md; el propietario puede revisarlo.
- **Fecha:** 2026-10-23
- **Decide:** Claude, dentro del mandato del propietario (prompt v3); revisión del propietario pendiente
- **Fuentes:** ADR-010 (principios de seguridad de la app), ADR-014 (Centro de Mando), `ops/secrets.md`; código en `src/trading/api/`

## Contexto

El Centro de Mando muestra el estado del sistema, los resultados y los reportes fiscales. Es para un solo usuario, el propietario, que lo consulta también desde el celular. No debe poder mover dinero ni relajar el riesgo, aunque alguien robe la sesión.

## Decisión

1. **Solo lectura respecto al dinero.** La API no tiene rutas para:
   - enviar órdenes,
   - activar `LIVE_TRADING`,
   - crear claves,
   - ni cambiar límites.

   Las únicas escrituras son la sesión (`POST`/`DELETE /api/sesion`) y las notas del diario (`POST /api/diario/notas`). Un test recorre todas las rutas y falla si aparece otra escritura o una ruta de escritura bajo `/api/riesgo`. La calculadora de riesgo es un `GET` que evalúa con el motor real y no guarda nada. Las acciones que hacen el sistema más seguro (pausar, apagar el nivel A) llegan en la F6 con su propio ADR.
2. **Red:** el servidor escucha solo en `127.0.0.1`.
   - Se accede desde el celular por **Tailscale** (recomendado) o por un **túnel SSH** (`ssh -L 8000:127.0.0.1:8000 vps`).
   - Nunca se publica el puerto en internet.
   - Sin autenticación, la configuración se niega a escuchar fuera de loopback.
3. **Autenticación de un solo usuario:**
   - Contraseña con hash **scrypt** (N = 2¹⁵, r = 8, p = 1) más **TOTP** (RFC 6238, 6 dígitos, ±30 s).
   - Tras 5 intentos fallidos en 5 minutos, se bloquea.
   - La sesión es un token firmado con HMAC-SHA256 en una cookie `HttpOnly`, `SameSite=Strict` y `Secure` detrás de HTTPS. Caduca a las 12 h.
4. **Secretos** (`TRADING_API_PASSWORD_HASH`, `TRADING_API_TOTP_SECRET`, `TRADING_API_SESSION_KEY`):
   - Se leen del entorno que prepara `sops exec-env` en tiempo de ejecución.
   - Nunca están en el código, en el frontend ni en los logs, y `repr` no los muestra.
   - Con la autenticación activa y sin secretos, la app no arranca.
5. **Navegador:**
   - CSP estricta (`default-src 'self'`, sin scripts de terceros, `frame-ancestors 'none'`), `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `nosniff` y `Permissions-Policy` restrictiva.
   - `Cache-Control: no-store` en la API.
   - Sin CORS: la app y la API comparten origen.
   - Toda escritura exige la cabecera `X-Brujula: 1` como defensa anti-CSRF, además de `SameSite=Strict`.
6. **Datos honestos:** cada respuesta declara su origen (`real`, `backtest` o `demo`), y la app marca lo demo con "DATOS DE DEMOSTRACIÓN".
7. **Dependencias:** `pip-audit` y `npm audit` en CI. Las versiones se fijan en `uv.lock` y `package-lock.json`.
8. **Modo local sin autenticación** (`TRADING_API_AUTH=disabled`): solo para desarrollo y tests E2E, y solo en 127.0.0.1.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Publicar la app en internet con HTTPS y contraseña | Más superficie de ataque. Tailscale da acceso privado sin abrir puertos |
| OAuth con un proveedor externo | Dependencia externa para un solo usuario, que además expone la identidad del propietario a un tercero |
| bcrypt o argon2 | Igual de válidos. scrypt está en la biblioteca estándar y no añade dependencias |
| Cookie sin `SameSite` con token CSRF | `SameSite=Strict` más la cabecera propia bastan para una app de un solo origen |

## Consecuencias

- **Positivas:** aunque se comprometa la sesión, no se puede operar ni relajar el riesgo desde la app. Los secretos no viven en el repositorio.
- **Negativas:** acceder desde el celular requiere instalar Tailscale (o un cliente SSH), y el TOTP añade un paso a cada inicio de sesión.
- **Pendiente:**
  - Generar los secretos con SOPS cuando el propietario tenga su clave age (F2).
  - Certificado HTTPS de Tailscale en el VPS (F6).
  - Acciones de seguridad (pausar, apagar el nivel A) en la F6.
