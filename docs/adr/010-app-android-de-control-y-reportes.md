# ADR-010: App Android de control, dashboard y reportes

- **Estado:** Aceptado (decisión del propietario del 23-oct-2026); **sustituido en parte por ADR-014** (23-oct-2026): la interfaz principal pasa a ser el Centro de Mando web y esta app queda como cliente ligero. Los principios de seguridad de este ADR siguen vigentes.
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Fuentes:** CLAUDE.md reglas 1 a 5; plan §4; ADR-006, ADR-008, ADR-009; especificación en `docs/app/especificacion.md`

## Contexto

El propietario quiere controlar el sistema desde el móvil (Android) en cualquier lugar: ver un resumen, entender cuántas decisiones se toman y cómo les va, ver cómo aprende el sistema en cada operación, aprobar o vetar señales y descargar reportes para impuestos.

## Decisión

1. **App nativa Android** en Kotlin con Jetpack Compose (Material 3). Se compila en GitHub Actions, que tiene el SDK de Android, y el APK de depuración se publica como artefacto del CI.
2. **El teléfono nunca tiene claves de exchange ni de wallets.** La app habla solo con el backend propio (VPS) por HTTPS; el backend es quien tiene las claves de solo operar (ADR-002, ADR-009).
3. **Asimetría de seguridad: apagar es fácil, encender es difícil.**
   - Desde la app se puede: activar el kill switch (bloquea entradas y cierra posiciones), pausar una estrategia, apagar el nivel A y rechazar o vetar señales.
   - Aprobar una señal de nivel B o encender el nivel A exige biometría y TOTP.
   - **No** se puede desde la app: activar `LIVE_TRADING` (regla 2: solo por CLI local con TOTP y commit firmado) ni cambiar límites de riesgo (regla 4: solo por ADR).
4. **Autenticación:** clave ligada al dispositivo (Android Keystore) desbloqueada con biometría, más TOTP para las acciones críticas. Todas las acciones de la app quedan en el registro de auditoría.
5. **Notificaciones:** Firebase Cloud Messaging con contenido mínimo ("hay una señal nueva"). El detalle se descarga por la API autenticada, así que la notificación nunca lleva datos sensibles.
6. **Chat de análisis:** solo lectura. Claude responde con datos calculados por el backend (regla 3: no inventa números ni probabilidades); no puede ejecutar acciones, y los datos externos se tratan como datos (regla 5).
7. **Datos honestos:** mientras no haya operaciones reales, la app muestra un aviso visible de "datos de demostración" o "simulación en sombra"; nunca presenta datos simulados como reales.
8. **Fases:** el esqueleto con datos de demostración se puede construir ya. El backend con API (FastAPI) llega con la F6, y los datos reales de sombra con la F7.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| App web instalable (PWA) | El propietario prefirió Android nativo |
| Multiplataforma (Flutter / React Native) | Solo se necesita Android; una capa más sin beneficio |
| Solo Telegram | Sin dashboard ni reportes descargables |
| Claves de exchange en el teléfono | Un teléfono perdido o comprometido daría acceso a operar |

## Consecuencias

- **Positivas:** control desde cualquier lugar; reportes fiscales a demanda; la seguridad no depende del teléfono.
- **Negativas:** se añade al stack Kotlin/Compose, Gradle y FCM. El esqueleto no se puede compilar en el contenedor de desarrollo (sin SDK de Android); su verificación es el CI.
- **Pendiente:** API del backend (F6), publicación del backend en el VPS con HTTPS y validación del formato de los reportes con el contador.
