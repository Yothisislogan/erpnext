#!/usr/bin/env bash
set -euo pipefail

export PATH="/home/frappe/.local/bin:/usr/local/bin:${PATH}"

BENCH_DIR="${BENCH_DIR:-/var/data/frappe-bench}"
SITE_NAME="${SITE_NAME:-${RENDER_EXTERNAL_HOSTNAME:-erpnext.local}}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-admin}"
FRAPPE_BRANCH="${FRAPPE_BRANCH:-develop}"
PORT="${PORT:-10000}"

MYSQL_DATA_DIR="/var/data/mysql"

log() {
  echo "[render-start] $*"
}

ensure_dirs() {
  mkdir -p "${MYSQL_DATA_DIR}" /var/data/redis /run/mysqld
  chown -R mysql:mysql "${MYSQL_DATA_DIR}" /run/mysqld
  chown -R frappe:frappe /var/data
}

start_mariadb() {
  ensure_dirs

  if [ ! -d "${MYSQL_DATA_DIR}/mysql" ]; then
    log "Initializing MariaDB data directory"
    mariadb-install-db --user=mysql --datadir="${MYSQL_DATA_DIR}" >/tmp/mariadb-install.log
    FIRST_DB_BOOT=1
  else
    FIRST_DB_BOOT=0
  fi

  log "Starting MariaDB"
  mysqld_safe --datadir="${MYSQL_DATA_DIR}" --socket=/run/mysqld/mysqld.sock --bind-address=127.0.0.1 &

  for _ in $(seq 1 60); do
    if mysqladmin ping --socket=/run/mysqld/mysqld.sock -uroot --silent >/dev/null 2>&1; then
      break
    fi
    if mysqladmin ping --socket=/run/mysqld/mysqld.sock -uroot -p"${MYSQL_ROOT_PASSWORD}" --silent >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done

  if [ "${FIRST_DB_BOOT}" = "1" ]; then
    log "Setting MariaDB root password"
    mysql --socket=/run/mysqld/mysqld.sock -uroot <<SQL
ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
CREATE USER IF NOT EXISTS 'root'@'127.0.0.1' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'127.0.0.1' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SQL
  fi
}

bench_cmd() {
  su frappe -c "cd ${BENCH_DIR} && $*"
}

init_bench_if_needed() {
  if [ -d "${BENCH_DIR}/apps/frappe" ]; then
    log "Existing bench found at ${BENCH_DIR}"
    return
  fi

  log "Creating Frappe bench at ${BENCH_DIR}"
  mkdir -p "$(dirname "${BENCH_DIR}")"
  chown -R frappe:frappe "$(dirname "${BENCH_DIR}")"

  su frappe -c "cd /var/data && bench init --frappe-branch ${FRAPPE_BRANCH} $(basename "${BENCH_DIR}")"

  log "Installing ERPNext from this repository"
  bench_cmd "bench get-app erpnext /opt/erpnext-source"

  log "Installing WIT custom app into bench"
  rm -rf "${BENCH_DIR}/apps/wit_insurance"
  cp -a /opt/erpnext-source/custom_apps/wit_insurance "${BENCH_DIR}/apps/wit_insurance"
  chown -R frappe:frappe "${BENCH_DIR}/apps/wit_insurance"

  bench_cmd "bench setup requirements"
}

create_site_if_needed() {
  if [ -d "${BENCH_DIR}/sites/${SITE_NAME}" ]; then
    log "Existing site found: ${SITE_NAME}"
    return
  fi

  log "Creating site ${SITE_NAME}"
  bench_cmd "bench new-site ${SITE_NAME} --db-host 127.0.0.1 --db-port 3306 --mariadb-root-password '${MYSQL_ROOT_PASSWORD}' --admin-password '${ADMIN_PASSWORD}' --no-mariadb-socket"

  log "Installing ERPNext app"
  bench_cmd "bench --site ${SITE_NAME} install-app erpnext"

  log "Installing WIT Insurance app"
  bench_cmd "bench --site ${SITE_NAME} install-app wit_insurance"
}

write_runtime_config() {
  log "Writing Render runtime Procfile on port ${PORT}"
  cat >"${BENCH_DIR}/Procfile" <<EOF
redis_cache: redis-server config/redis_cache.conf
redis_queue: redis-server config/redis_queue.conf
redis_socketio: redis-server config/redis_socketio.conf
web: bench serve --host 0.0.0.0 --port ${PORT} --noreload --nothreading
socketio: node apps/frappe/socketio.js
schedule: bench schedule
worker_short: bench worker --queue short
worker_default: bench worker --queue default
worker_long: bench worker --queue long
EOF
  chown frappe:frappe "${BENCH_DIR}/Procfile"

  echo "${SITE_NAME}" >"${BENCH_DIR}/sites/currentsite.txt"
  chown frappe:frappe "${BENCH_DIR}/sites/currentsite.txt"

  bench_cmd "bench --site ${SITE_NAME} set-config host_name https://${SITE_NAME}"
  bench_cmd "bench --site ${SITE_NAME} migrate"
  bench_cmd "bench --site ${SITE_NAME} clear-cache"
}

main() {
  log "Starting Render staging boot for site ${SITE_NAME}"
  start_mariadb
  init_bench_if_needed
  create_site_if_needed
  write_runtime_config

  log "Starting Frappe bench"
  exec su frappe -c "cd ${BENCH_DIR} && bench start"
}

main "$@"
