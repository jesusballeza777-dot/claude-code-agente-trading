# ADR-014: Centro de Mando web como app principal; Android como cliente ligero

- **Estado:** Aceptado (decisión del propietario del 23-oct-2026: "web principal + Android")
- **Fecha:** 2026-10-23
- **Decide:** propietario del proyecto
- **Sustituye en parte a:** ADR-010 (la app Android deja de ser la interfaz principal; sus principios de seguridad siguen vigentes)
- **Fuentes:** prompt v3 del propietario §4; ADR-010, ADR-011; seguridad en ADR-015

## Contexto

El propietario quiere un "Centro de Mando" visual, atractivo y amigable: dashboards, laboratorio de estrategias, calculadora de riesgo con el motor real, diario, proyecto y reportes descargables. El ADR-010 había elegido una app Android nativa, que obliga a duplicar la lógica de presentación y no se puede compilar en el entorno de desarrollo. Ante el conflicto, el propietario eligió web principal + Android como cliente ligero.

## Decisión

1. **Centro de Mando web** (`app/web/`) como interfaz principal, responsive, usable desde el navegador del celular a través de Tailscale o de un túnel SSH (ADR-015).
2. **Backend:** FastAPI + Pydantic v2 en `src/trading/api/`.
   - Solo lectura respecto al dinero.
   - Importa el motor de riesgo real para la calculadora.
   - Decimales serializados como texto.
   - Lee Parquet, `research/` y `docs/`.
3. **Frontend:** React + Vite + TypeScript, con:
   - Tailwind CSS y tokens de diseño propios.
   - Componentes accesibles sobre Radix (al estilo shadcn/ui).
   - TanStack Query, Framer Motion e iconos Lucide.
4. **Gráficas:** TradingView Lightweight Charts (Apache-2.0, con la atribución que exige su licencia) para velas; Recharts para métricas, curvas y heatmaps.
5. **Tests:** Vitest + Testing Library; Playwright E2E con capturas en claro, oscuro y móvil, más chequeo de accesibilidad con axe.
6. **Copiloto:** "Brújula", con textos generados por plantillas deterministas. Claude no aporta números a la app.
7. **App Android:** se mantiene como **cliente ligero** de la misma API en la F6 (alertas, kill switch y apagar el nivel A). Su esqueleto actual sigue compilándose en CI.
8. Las versiones se fijan en los lockfiles (`uv.lock`, `package-lock.json`).

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Solo Android nativo (ADR-010) | Rechazado por el propietario. Duplica la presentación y no se puede compilar ni probar visualmente en el entorno de desarrollo |
| Grafana | Excelente para métricas de infraestructura (se usará en la F6). No sirve para la narrativa, el copiloto, la calculadora interactiva con el motor real, el laboratorio con IC ni los reportes con identidad propia |
| Streamlit | Rápido para prototipos, pero da poco control de diseño, accesibilidad y experiencia móvil; además, su modelo de re-ejecución complica la seguridad y los tests E2E |
| Next.js | Su renderizado en servidor no aporta nada a una app de un solo usuario detrás de Tailscale; Vite es más simple |

## Consecuencias

- **Positivas:** una sola interfaz rica, probada con E2E y capturas; el celular la usa desde el navegador sin tienda de apps.
- **Negativas:** se añaden al stack Node, React y su cadena de herramientas, con `npm audit` en el CI.
- **Pendiente:** publicar el backend en el VPS (F6) y la app Android como cliente ligero (F6).
