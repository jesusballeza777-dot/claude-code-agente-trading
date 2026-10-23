# App Android: Agente Trading

Esqueleto de la app de control (ADR-010; especificación en `docs/app/especificacion.md`).

- **Estado:** datos de demostración, con un aviso visible en todas las pantallas. Sin permiso de Internet ni conexión al backend.
- **Pantallas:** Resumen, Decisiones, Aprendizaje, Reportes y Controles (estos últimos desactivados hasta la F6).
- **Seguridad:** el teléfono nunca tiene claves de exchange ni de wallets. `LIVE_TRADING` y los límites de riesgo no se pueden cambiar desde la app.

## Compilar

Necesita JDK 17 y el SDK de Android (`ANDROID_HOME`).

```bash
cd app/android
./gradlew assembleDebug testDebugUnitTest
```

El CI (`.github/workflows/ci.yml`, job `android`) compila, ejecuta los tests y publica el APK de depuración como
artefacto `app-debug-apk`. Para instalarlo: descargar el artefacto desde la ejecución del CI en GitHub y abrir el
APK en el teléfono (permitiendo la instalación desde esa fuente).

## Dependencias y por qué

| Dependencia | Para qué |
|---|---|
| Android Gradle Plugin 8.7.3, Kotlin 2.0.21 | Compilar la app |
| Jetpack Compose (BOM 2024.12.01), Material 3, iconos básicos | Interfaz declarativa estándar de Android |
| activity-compose 1.9.3 | Arrancar Compose desde la actividad |
| JUnit 4.13.2 | Tests de formato |
