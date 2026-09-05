# m4b-tool depends on mp4v2 and fdkaac, neither of which are packaged for
# Debian/Ubuntu anymore (patent/licensing reasons). The upstream m4b-tool
# project instead publishes prebuilt Alpine-based tool images for these, so we
# pull the binaries from those images (same approach as m4b-tool's own
# official Dockerfile) and run on an Alpine base ourselves for ABI compatibility.
FROM sandreas/tone:v0.2.5 AS tone
FROM sandreas/mp4v2:2.1.1 AS mp4v2
FROM sandreas/fdkaac:2.0.1 AS fdkaac

# Use an official Python runtime as a parent image
FROM python:3.11-alpine

# Add labels for container metadata
LABEL org.opencontainers.image.title="AudiobookBay Automated"
LABEL org.opencontainers.image.description="Search AudiobookBay, download via your torrent client of choice, and automatically organize/tag/move completed audiobooks into your library."
LABEL org.opencontainers.image.source="https://github.com/zprough/audiobookbay-automated"
LABEL org.opencontainers.image.licenses="MIT"

# Ensure Python output is not buffered so logs appear immediately in Docker
ENV PYTHONUNBUFFERED=1
ENV M4B_TOOL_VERSION=v0.5.2

# System dependencies:
#  - ffmpeg / php83-*: required by m4b-tool for merging/converting audiobooks
#  - libstdc++ / libgomp: runtime libs needed by the mp4v2/fdkaac binaries below
#  - wget / ca-certificates: fetching the m4b-tool.phar release
#  - supervisor: runs the web app and the agent worker as two supervised processes
#  - 7zip: extracts .rar/.zip/.7z downloads (AudiobookBay often ships these
#    instead of raw audio files) before the agent scans for audio files
RUN apk add --no-cache --update \
        ffmpeg \
        libstdc++ \
        libgomp \
        php83-cli \
        php83-curl \
        php83-dom \
        php83-xml \
        php83-mbstring \
        php83-openssl \
        php83-phar \
        php83-simplexml \
        php83-tokenizer \
        php83-xmlwriter \
        php83-zip \
        wget \
        ca-certificates \
        supervisor \
        7zip \
    && ln -sf /usr/bin/php83 /usr/bin/php

# Copy prebuilt tone / mp4v2 / fdkaac binaries (and mp4v2's shared libs) from
# the upstream m4b-tool tool images.
COPY --from=tone /usr/local/bin/tone /usr/local/bin/tone
COPY --from=mp4v2 /usr/local/bin/mp4* /usr/local/bin/
COPY --from=mp4v2 /usr/local/lib/libmp4v2* /usr/local/lib/
COPY --from=fdkaac /usr/local/bin/fdkaac /usr/local/bin/fdkaac
RUN chmod +x /usr/local/bin/tone /usr/local/bin/mp4* /usr/local/bin/fdkaac

# Install m4b-tool (architecture-independent PHP phar)
RUN wget -q "https://github.com/sandreas/m4b-tool/releases/download/${M4B_TOOL_VERSION}/m4b-tool.phar" -O /usr/local/bin/m4b-tool \
    && chmod +x /usr/local/bin/m4b-tool

# Set the working directory in the container
WORKDIR /app

# Install Python dependencies (copy requirements first for layer caching)
COPY app/requirements.txt /tmp/app-requirements.txt
COPY agent/requirements.txt /tmp/agent-requirements.txt
RUN pip install --no-cache-dir -r /tmp/app-requirements.txt -r /tmp/agent-requirements.txt

# Copy the Flask web app contents into the container (flattened into /app)
COPY app /app

# Copy the agent package (nested under /app/agent so `python -m agent.main` resolves)
COPY agent /app/agent

# Copy helper scripts (e.g. agent-healthcheck.sh)
COPY scripts /app/scripts

# Copy the process supervisor configuration
COPY supervisord.conf /app/supervisord.conf

# Expose the port the web app runs on
EXPOSE 5078

# Healthcheck verifies the agent's required directories are present/writable
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD sh /app/scripts/agent-healthcheck.sh || exit 1

# Run both the web app and the agent worker under supervisord
CMD ["supervisord", "-c", "/app/supervisord.conf"]
