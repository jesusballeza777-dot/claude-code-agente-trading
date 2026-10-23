# ADR-016: Datos públicos de la F3 y almacenamiento (Parquet + TimescaleDB)

- **Estado:** Aceptado. Aplica decisiones ya aprobadas (ADR-012: F3 solo con datos públicos y sin claves; prompt v3 del propietario, Ola 5). No toca límites de riesgo ni el pre-registro.
- **Fecha:** 2026-10-23
- **Decide:** Claude, dentro del mandato del ADR-012; el propietario puede revisarlo
- **Fuentes:** CLAUDE.md reglas 1, 5, 6, 7 y 8; ADR-012; `research/preregistration/ACLARACIONES-v1.md` §1, §2 y §6; auditoría A-01 y A-21; código en `src/trading/data/`

## Contexto

La F3 necesita velas y funding de 2019-2024 sin claves y sin tocar el holdout. Además:

- el archivo público de Binance (`data.binance.vision`) no es accesible directamente desde el entorno de desarrollo, pero su espejo en S3 sí;
- los formatos cambian con los años (cabeceras, microsegundos);
- el universo de H2 debe construirse *point-in-time*, con los contratos deslistados;
- y el prompt v3 pide Parquet particionado más PostgreSQL + TimescaleDB por Docker Compose.

## Decisión

1. **Fuente:** solo el archivo público por su espejo `s3-ap-northeast-1.amazonaws.com/data.binance.vision`.
   - Prefijos permitidos en código: velas mensuales spot, velas mensuales de perpetuos USDⓈ-M y funding mensual.
   - Cualquier otro prefijo o host lanza un error. Un test de gobernanza comprueba que la capa de datos no contiene otras URL ni endpoints de cuenta, órdenes, retiro o transferencia.
2. **Integridad:**
   - Cada zip se verifica con su `.CHECKSUM` SHA-256 y, si no cuadra, se descarta.
   - Las descargas son idempotentes y reintentan los cortes de red con espera exponencial (2, 4, 8 y 16 s).
   - `data/manifest.json` guarda la clave y el SHA-256 de cada fichero. El **id del dataset** es el SHA-256 del manifiesto ordenado; cada fila de `trials.csv` lo anota.
3. **Holdout:**
   - La F3 descarga solo meses hasta 2024-12 (ACLARACIONES §6.11): los ficheros del holdout no se descargan.
   - Toda lectura de investigación pasa por `trading.data.holdout.ensure_research_window`, que rechaza instantes ≥ 2025-01-01 salvo autorización firmada (`research/holdout_unlock.toml` en un commit firmado por una clave de `ops/allowed_signers`, que solo añade el propietario).
4. **Almacenamiento:**
   - **Parquet es la fuente de verdad** de la investigación, en `data/parquet/klines/<mercado>/<intervalo>/<SÍMBOLO>.parquet` y `data/parquet/funding/<SÍMBOLO>.parquet`, particionado por mercado, intervalo y símbolo.
   - **TimescaleDB es una copia** para consultas y para el Centro de Mando (hypertables `klines` y `funding`). Se carga con `python -m trading.data.timescale` leyendo con la guardia.
   - `data/` no se versiona.
5. **Tipos:** precios y volúmenes en `float64`.
   - Al leer cada CSV se comprueba que cada precio vuelve exacto a su texto (`Decimal(repr(float(x))) == Decimal(x)`); con ≤15 cifras significativas no se pierde nada.
   - El informe de calidad publica cuántos precios no cumplen.
   - El backtester convierte a `Decimal` antes de llamar al motor de riesgo.
6. **Calidad:** por serie se cuentan huecos, duplicados, desorden, desalineación con la rejilla UTC, `close_time` incoherente y OHLC imposible. Objetivo de completitud: > 99.5%. Informe en `docs/datos/calidad-f3.md`; validación cruzada del cierre diario spot frente a perpetuo de BTC y ETH.
7. **Universo point-in-time de H2:** se construye con `trading.data.universe` siguiendo ACLARACIONES §2, solo con velas anteriores a cada fecha de reconstitución, e incluye deslistados. Tabla en `docs/datos/universo-h2-v1.md`.
8. **Base local sin secretos:**
   - En desarrollo, `docker compose up db` levanta TimescaleDB 2.17.2 (PostgreSQL 16) escuchando solo en 127.0.0.1, sin contraseña y con datos públicos.
   - En el VPS la base no publica puerto y la contraseña se lee desde SOPS (F6).

### Dependencias nuevas (CLAUDE.md: justificar cada una)

| Dependencia | Problema que resuelve |
|---|---|
| polars | Lectura y escritura de Parquet, filtros perezosos con la guardia y agregaciones del universo y de la calidad, sin pandas ni pyarrow |
| psycopg (binario) | Carga en PostgreSQL con `COPY`, el método más rápido y sin ORM |

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Solo PostgreSQL | El backtest leería la base en cada corrida; Parquet es más simple de versionar por id de dataset y no necesita un servidor |
| DuckDB en lugar de TimescaleDB | Era el respaldo previsto si no hubiera Docker. Docker está disponible y el prompt pide TimescaleDB |
| pandas + pyarrow | Dos dependencias grandes para lo que polars hace solo |
| Guardar precios como `Decimal128` en Parquet | Más pesado y menos compatible. La comprobación de ida y vuelta garantiza que `float64` no pierde precisión en los precios de Binance |
| Descargar también el holdout y aislarlo | Permitido por el prompt, pero innecesario en la F3. No descargarlo elimina el riesgo de mirarlo por error |

## Consecuencias

- **Positivas:** datos reproducibles (cualquiera puede volver a descargar y comparar el id del dataset); la guardia del holdout está en el código; no hay claves ni endpoints privados.
- **Negativas:** la validación cruzada usa la misma fuente (spot frente a perpetuo); una segunda fuente independiente queda **por verificar**. La base local sin contraseña solo es aceptable porque escucha en 127.0.0.1 y contiene datos públicos.
- **Pendiente:**
  - Descargar el holdout en el gate de la F4, con autorización firmada.
  - Comparar con una segunda fuente independiente.
  - Velas de 1h para el disyuntor de volatilidad del ADR-013 (cuando se aprueben sus reglas).
