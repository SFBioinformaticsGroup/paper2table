FROM python:3.13-slim

# LLM provider packages to install in addition to the base dependencies.
# Override at build time to add other providers, e.g.:
#   docker build --build-arg EXTRA_PACKAGES="openai" ...
#   docker build --build-arg EXTRA_PACKAGES="google-genai openai" ...
#   docker build --build-arg EXTRA_PACKAGES="" ...  (no provider)
ARG EXTRA_PACKAGES="google-genai"
# spaCy language models to download; set to "" to skip
ARG SPACY_MODELS="en_core_web_md es_core_news_md"

RUN apt-get update && apt-get install -y --no-install-recommends \
        ghostscript \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies
COPY setup.cfg pyproject.toml ./
RUN mkdir -p src && \
    SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 pip install --no-cache-dir . && \
    rm -rf src/

# Install LLM provider packages
RUN if [ -n "$EXTRA_PACKAGES" ]; then pip install --no-cache-dir $EXTRA_PACKAGES; fi

# Download spaCy language models
RUN if [ -n "$SPACY_MODELS" ]; then for model in $SPACY_MODELS; do python -m spacy download $model; done; fi

# Install package
COPY . .
RUN SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0 pip install --no-cache-dir --no-deps .

COPY docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /data
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
