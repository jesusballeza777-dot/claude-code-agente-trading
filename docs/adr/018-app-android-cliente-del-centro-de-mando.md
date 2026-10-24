# ADR-018: App Android como cliente nativo del Centro de Mando

- **Estado:** Aceptado (el propietario pidió el 24-oct-2026 una app de celular personal, visualmente atractiva, con acceso a todo y en tiempo casi real)
- **Fecha:** 2026-10-24
- **Decide:** propietario del proyecto
- **Sustituye en parte a:** ADR-010 (esqueleto Android con datos de demostración) y concreta el punto 7 del ADR-014
- **Fuentes:** ADR-009, ADR-014, ADR-015; CLAUDE.md reglas 1, 2 y 8

## Contexto

El esqueleto de la app Android (ADR-010) tenía cinco pantallas básicas con datos de demostración y no se conectaba a nada. El Centro de Mando web ya tiene las diez páginas, las gráficas, el laboratorio, la calculadora con el motor de riesgo real y los reportes. Mantener dos interfaces con la misma lógica de presentación duplica el trabajo y deja la del celular siempre atrasada.

## Decisión

1. **La app Android es un cliente nativo del Centro de Mando, que pasa a nativo página por página.**
   - **Etapa 1 (hecha):** muestra el mismo sitio en un `WebView` endurecido, así que tiene todas las páginas y se actualiza con la web sin publicar otro APK.
   - **Etapa 2 (hecha):** **todas** las páginas del Centro de Mando son pantallas nativas (Compose): Hoy, En vivo, Laboratorio, Riesgo (con la calculadora del motor real), Mercado (velas, funding, regímenes y correlaciones dibujados en la app), Decisiones, Diario, Proyecto, Reportes y Ajustes. Leen la API con un cliente HTTP propio, sin puente JavaScript. Un test de contrato en Python (`tests/api/test_android_contract.py`) falla si un cambio de la API rompe lo que la app lee. El `WebView` queda solo como salida opcional ("Abrir el Centro de Mando web", en Ajustes).
   - **Etapa 3 (pendiente):** notificaciones (F6) y, si se decide en la F6, una fuente de datos local en el teléfono (ver el ADR de ejecución).
2. **Lo nativo se limita a lo que el navegador no da bien:**
   - Pantalla de conexión que comprueba que la dirección es de verdad un Centro de Mando antes de guardarla.
   - Bloqueo con huella, rostro o PIN del teléfono (se pide al abrir y al volver tras un minuto fuera).
   - Ocultar la app en "recientes" y bloquear capturas (se puede desactivar).
   - Arrastrar para actualizar, botón atrás, descarga de reportes a la carpeta Descargas y pantalla de error con reintento.
   - Icono adaptable y tema oscuro desde el primer fotograma.
3. **Tiempo casi real:** la pantalla **En vivo** sondea `/api/en-vivo` cada 5 s y **Hoy** cada 30 s, solo con la app al frente. Si el servidor deja de responder se conserva el último dato con un aviso, sin inventar nada. Con la autenticación activa, la app pide contraseña y código TOTP y comparte la sesión con el `WebView`; la sesión vive solo en memoria.
4. **Seguridad del cliente:**
   - Solo HTTPS, salvo `127.0.0.1` y `localhost` (lo que da `adb reverse` por USB); lo aplican la validación de la dirección y la configuración de seguridad de red.
   - El `WebView` nunca sale del servidor propio: otros sitios https se abren en el navegador y todo lo demás se bloquea. Sin acceso a ficheros y sin contenido mixto.
   - **Sin puente JavaScript:** la página no puede llamar a código nativo. El único enlace hacia la app es `brujula://ajustes`, que solo abre los ajustes.
   - La sesión (contraseña + TOTP, ADR-015) vive en la cookie del `WebView`. Cambiar de servidor la borra.
   - Sin claves de exchanges ni de wallets en el teléfono y sin permisos más allá de INTERNET. La app hereda la regla de solo lectura de la API: no puede enviar órdenes, activar `LIVE_TRADING`, crear claves ni cambiar límites.
5. **Honestidad de los datos:** En vivo muestra qué piezas existen y cuáles no (exchanges "no conectado", analista y sombra "no iniciado"). Las decisiones del analista salen rotuladas como demostración hasta la F5.
6. **También se puede instalar la web como app** desde el navegador (manifest e iconos), como alternativa sin APK.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Reescribir las diez páginas en Kotlin y Compose | Duplica la presentación, tarda semanas y queda siempre por detrás de la web. Se puede revisar cuando haya uso diario que lo justifique |
| Capacitor o React Native | Añaden una cadena de herramientas grande para lo que hace el `WebView`; la validación de dirección, el bloqueo y la política de navegación son pocas líneas nativas |
| Solo PWA | Sin bloqueo biométrico propio ni control de qué direcciones se abren; se mantiene como alternativa |
| Notificaciones push desde ya | Necesitan servidor de envío y reglas de alerta; llegan con la F6 junto con las alertas de riesgo |

## Consecuencias

- **Positivas:** el celular tiene todo lo del Centro de Mando y mejora cada vez que mejora la web; la superficie nativa es pequeña y tiene tests de JVM (dirección, política de navegación y bloqueo).
- **Negativas:** sin conexión no hay datos (no se guarda caché de información financiera en el teléfono); las descargas dependen del gestor de descargas del sistema.
- **Pendiente:**
  - **Por verificar** en un teléfono real: el flujo completo (conexión, bloqueo, descargas) y el comportamiento con HTTP hacia `127.0.0.1` en el gestor de descargas.
  - Notificaciones y alertas (F6).
  - Firma de release con una clave del propietario; el APK de CI es de depuración.
