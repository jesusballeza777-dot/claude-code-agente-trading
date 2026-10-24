# Backend del Centro de Mando (FastAPI). Solo lectura respecto al dinero (ADR-014, ADR-015).
FROM python:3.12-slim

# Pango y fuentes para los PDF de WeasyPrint (ADR-017). Repositorios por HTTPS.
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.11.32
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev

# Sin git en la imagen: el commit del código para la procedencia de los reportes llega del build.
ARG CODE_COMMIT=desconocido
ENV TRADING_CODE_COMMIT=$CODE_COMMIT

# Estado de la app (notas, auditoría, historial de reportes) en su propio volumen; los datos de
# mercado se montan de solo lectura.
RUN useradd --create-home --uid 1000 centro && mkdir -p /app/state && chown centro /app/state
USER centro

# El servidor escucha solo en el loopback del contenedor; nginx (mismo espacio de red) lo
# publica. Sin autenticación solo en local: en el VPS se usa TRADING_API_AUTH=on con SOPS.
ENV TRADING_API_HOST=127.0.0.1 TRADING_API_PORT=8000 TRADING_APP_STATE=/app/state
CMD ["uv", "run", "--frozen", "--no-sync", "python", "-m", "trading.api"]
