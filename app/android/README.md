# App Android: Brújula

Cliente nativo y de solo lectura del Centro de Mando (ADR-018). Es la app de celular personal del propietario.

- **Qué hace:** abre tu Centro de Mando con bloqueo por huella, rostro o PIN. Todas las páginas son pantallas nativas:
  **Hoy**, **En vivo** (se actualiza cada 5 s con la app al frente), **Laboratorio** (hipótesis, gate y gráficas),
  **Riesgo** (calculadora con el motor real, límites y vetos), **Mercado** (velas con el canal de H2, funding, regímenes y
  correlaciones), **Decisiones**, **Diario** (con notas), **Proyecto**, **Reportes** (descarga PDF, Excel y CSV) y **Ajustes**.
  Si tu servidor tiene la autenticación activa, pide contraseña y código TOTP una sola vez por sesión.
  Desde Ajustes también puedes abrir el Centro de Mando web completo dentro de la app.
- **Qué no hace:** no envía órdenes, no activa `LIVE_TRADING`, no crea claves ni cambia límites, y no guarda claves de
  exchanges ni de wallets. Su único permiso es INTERNET.
- **Datos:** vienen del servidor. Hoy el servidor es tu computadora (por cable USB) o, cuando exista, tu VPS con Tailscale.

## Instalar el APK

1. En GitHub, abre la última ejecución verde del workflow **CI** de la rama y descarga el artefacto `app-debug-apk`
   (hay que iniciar sesión en GitHub; caduca a los 14 días).
2. Descomprime el ZIP y abre `app-debug.apk` en el teléfono, permitiendo instalar desde esa fuente.
3. Es un APK de depuración: sirve para uso personal. La firma de release con tu propia clave queda pendiente.

## Sin servidor

Al abrir la app por primera vez toca **Usar sin servidor**: no pide ninguna dirección. Lleva dentro los resultados reales de la F4,
el estado del proyecto, los límites y tus notas (se guardan en el teléfono). **Necesitan servidor:** la calculadora del motor de
riesgo, los datos de mercado (≈200 MB) y los reportes; la app lo dice donde corresponde. Los datos incluidos son los del commit
con el que se compiló el APK (la franja de arriba dice cuándo). Se generan en la CI con `ops/android_snapshot.py`; una compilación
local sin ese paso no los incluye.

## Conectar un servidor

**Por cable USB, sin red** (con el Centro de Mando corriendo en tu computadora con `docker compose up`):

```bash
adb reverse tcp:8080 tcp:8080     # el teléfono ve el puerto 8080 de tu computadora como 127.0.0.1:8080
```

En la app escribe `127.0.0.1:8080`. El teléfono necesita la depuración USB activada solo para este paso.

**Desde cualquier lugar** (cuando exista el VPS): instala Tailscale en el servidor y en el teléfono, ejecuta
`tailscale serve --bg 8080` en el servidor y escribe `https://tu-servidor.tu-red.ts.net`. Con la autenticación activa
(`TRADING_API_AUTH=on`) la app mostrará el acceso con contraseña y código TOTP. Ver el README principal.

Para cambiar de servidor o del bloqueo: Ajustes de la web → "Servidor, bloqueo y privacidad".

## Compilar

Necesita JDK 17 y el SDK de Android (`ANDROID_HOME`).

```bash
cd app/android
./gradlew assembleDebug testDebugUnitTest
```

El CI (job `android`) compila, ejecuta los tests y publica el APK. Los tests de JVM (72) cubren la validación de la dirección,
la política de navegación del WebView, el bloqueo, el cliente HTTP con inicio de sesión (contra un servidor local), la lectura de las respuestas
reales de la API y el formato; la interfaz y el WebView se comprobarán en un teléfono real
(**por verificar**: este entorno no tiene SDK de Android).

## Dependencias y por qué

| Dependencia | Para qué |
|---|---|
| Android Gradle Plugin 8.7.3, Kotlin 2.0.21 | Compilar la app |
| Jetpack Compose (BOM 2024.12.01), Material 3, iconos básicos | Pantallas de conexión, bloqueo y error |
| activity-compose 1.9.3, fragment 1.8.5 | Actividad con Compose y base para el diálogo biométrico |
| biometric 1.1.0 | Huella, rostro o PIN del teléfono |
| swiperefreshlayout 1.1.0 | Arrastrar para actualizar sobre el WebView |
| JUnit 4.13.2, org.json (solo tests) | Tests de la lógica, incluidos los del cliente HTTP contra un servidor local |
