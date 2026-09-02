FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ghostscript \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 \
    pip install --no-cache-dir .

COPY docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /data
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
