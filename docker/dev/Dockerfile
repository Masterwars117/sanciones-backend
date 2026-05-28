#Es debian
FROM python:3.10-slim-bookworm

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Oracle Instant Client: requerido por python-oracledb en thick mode (Oracle 10g).
# El .zip no existe en los repos de Debian, se baja del sitio oficial de Oracle.
ARG ORACLE_IC_DIR=instantclient_19_31
ARG ORACLE_IC_URL=https://download.oracle.com/otn_software/linux/instantclient/1931000/instantclient-basic-linux.x64-19.31.0.0.0dbru.zip
ENV ORACLE_CLIENT_LIB_DIR=/opt/oracle/${ORACLE_IC_DIR}

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git openssh-client \
        ca-certificates curl unzip \
        libaio1 \
    && rm -rf /var/lib/apt/lists/*

# Descarga, descomprime y registra el Instant Client en el linker dinámico.
RUN set -eux; \
    mkdir -p /opt/oracle; \
    curl -fsSL -o /tmp/instantclient.zip "${ORACLE_IC_URL}"; \
    unzip -q /tmp/instantclient.zip -d /opt/oracle; \
    rm -f /tmp/instantclient.zip; \
    test -d "${ORACLE_CLIENT_LIB_DIR}"; \
    echo "${ORACLE_CLIENT_LIB_DIR}" > /etc/ld.so.conf.d/oracle-instantclient.conf; \
    ldconfig

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -r requirements.txt
