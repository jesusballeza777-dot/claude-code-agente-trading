# ADR-017: Reportes descargables (PDF, XLSX, CSV, JSON y Parquet)

- **Estado:** Aceptado. Aplica el prompt v3 §5; el formato fiscal queda pendiente de validar con el contador.
- **Fecha:** 2026-10-23
- **Decide:** Claude, dentro del mandato del propietario; revisión del propietario pendiente
- **Fuentes:** prompt v3 §5; ADR-010 punto 7; auditoría A-18 y A-22; código en `src/trading/reporting/` y `src/trading/api/reports.py`

## Contexto

El propietario necesita reportes semanales y mensuales, una ficha por estrategia, un reporte para su contador, la exportación de la auditoría y la de los datos. Todos deben dejar claro de dónde salen sus cifras y si son de demostración.

## Decisión

1. **Formatos:**
   - PDF con plantillas HTML (Jinja2) renderizadas con **WeasyPrint**.
   - XLSX con **openpyxl**.
   - CSV, JSON y Parquet con la biblioteca estándar y polars.
2. **Procedencia en todos:** fecha UTC, commit del código, versión del pre-registro y de los límites, origen de los datos, marca DEMO si aplica y el aviso "No es asesoría financiera, legal ni fiscal". En el XLSX va en una hoja "Procedencia"; en el PDF, en una tabla al final y en el pie de cada página.
3. **Identidad visual:** la del Centro de Mando (azul petróleo y acento turquesa), en versión clara para imprimir. Las curvas se dibujan como SVG generado por el propio código, sin librerías de gráficos.
4. **Reporte para el contador:**
   - Una fila por operación: fecha fiscal en Ciudad de México, activo, tipo (spot o perpetuo), dirección, cantidad, precios, comisiones, funding y resultado en USD y en MXN.
   - El tipo de cambio es el **FIX de Banxico (serie SF43718)** del día o el último publicado. Si no se tiene, la columna queda vacía y dice **"por completar"**: nunca se inventa un tipo de cambio.
   - Mientras no haya operaciones reales, usa las del backtest, marcado DEMO, para que el contador valide el formato.
5. **Auditoría:** exportación JSON y CSV con **hashes encadenados** (`trading.audit.log`): cada entrada guarda el hash de la anterior, y `verify_chain` detecta cambios, borrados o reordenamientos. El registro en disco es append-only (JSON Lines).
6. **Generación al vuelo:**
   - Los reportes se generan al pedirlos (`GET /api/reportes/{tipo}/{formato}`) y no se guardan.
   - El historial (fecha, tipo, archivo, DEMO y SHA-256 del contenido) se anota en `data/app/reportes.jsonl`.

### Dependencias nuevas

| Dependencia | Problema que resuelve |
|---|---|
| jinja2 | Plantillas HTML con escape automático para los PDF |
| weasyprint | PDF a partir de HTML/CSS. Usa Pango, disponible en el entorno y en el contenedor |
| openpyxl | XLSX con formato (cabeceras, anchos, paneles fijos) |

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| ReportLab | Obliga a maquetar a mano; las plantillas HTML se mantienen mejor y reutilizan el estilo de la app |
| Navegador headless (Playwright) para el PDF | Mucho más pesado en producción |
| Guardar cada reporte generado | No hace falta: se regeneran a demanda y el historial guarda su huella SHA-256 |

## Consecuencias

- **Positivas:** reportes reproducibles y trazables; el contador puede validar el formato antes de la F8.
- **Negativas:** WeasyPrint necesita bibliotecas del sistema (Pango) en la imagen de Docker.
- **Pendiente:**
  - Descargar el FIX de Banxico (requiere token del SIE; **por verificar** desde el VPS).
  - Validar el formato con el contador.
  - Llenar el reporte con operaciones de sombra (F7) y reales (F8).
