FROM frappe/bench:latest

USER root

ENV DEBIAN_FRONTEND=noninteractive \
    BENCH_DIR=/var/data/frappe-bench \
    PORT=10000 \
    FRAPPE_BRANCH=develop

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        mariadb-server \
        redis-server \
        procps \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . /opt/erpnext-source
COPY render/start.sh /usr/local/bin/render-start

RUN chmod +x /usr/local/bin/render-start \
    && mkdir -p /var/data /run/mysqld \
    && chown -R frappe:frappe /var/data /opt/erpnext-source \
    && chown -R mysql:mysql /run/mysqld

EXPOSE 10000

CMD ["render-start"]
