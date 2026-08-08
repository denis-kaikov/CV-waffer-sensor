# Unofficial Daheng Galaxy SDK runtime image.
# Pin the version instead of using :latest for reproducible industrial builds.
FROM lensorai/docker-daheng-sdk:2.4.2503 AS daheng-sdk

FROM python:3.8-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KMZ_CONFIG=/app/config/config.yaml \
    LD_LIBRARY_PATH=/usr/local/lib/daheng:/usr/lib:/usr/local/lib \
    GENICAM_GENTL64_PATH=/usr/local/lib/daheng

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libglib2.0-0 \
    libgl1 \
    libusb-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy only the Galaxy SDK runtime delivered by the unofficial image.
RUN mkdir -p /usr/local/lib/daheng /etc/security/limits.d
COPY --from=daheng-sdk /usr/lib/libgxiapi.so /usr/local/lib/daheng/
COPY --from=daheng-sdk /usr/lib/GxGVTL.cti /usr/local/lib/daheng/
COPY --from=daheng-sdk /usr/lib/GxU3VTL.cti /usr/local/lib/daheng/
COPY --from=daheng-sdk /etc/security/limits.d/galaxy-limits.conf /etc/security/limits.d/

RUN echo '/usr/local/lib/daheng' > /etc/ld.so.conf.d/daheng.conf && ldconfig

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# The unofficial SDK image contains native Galaxy libraries, but not necessarily
# the official gxipy Python package. Put the gxipy wheel or source package into
# vendor/gxipy/. The conditional command keeps mock-mode builds operational.
COPY vendor/gxipy /tmp/gxipy
RUN if find /tmp/gxipy -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name '*.zip' \) | grep -q .; then \
        package="$(find /tmp/gxipy -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name '*.zip' \) | head -n 1)"; \
        pip install --no-cache-dir "$package"; \
    else \
        echo 'WARNING: gxipy package was not supplied; Daheng driver will be unavailable, mock/file drivers remain usable.'; \
    fi \
    && rm -rf /tmp/gxipy

COPY app ./app
COPY config ./config

CMD ["python", "-m", "app.main"]
