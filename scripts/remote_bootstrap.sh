#!/usr/bin/env bash
# Copyright (c) 2026, BIT Technologies GmbH and contributors
# License: AGPL-3.0-or-later
#
# Provisions a full Frappe/ERPNext v15 bench on a FRESH Ubuntu 22.04 host,
# installs erpnext_es_aeat from a zip, and runs both the offline regression
# and the live in-ERPNext check. Designed for a DISPOSABLE box.
#
# Usage (as a sudo-capable user, e.g. root):
#   ./remote_bootstrap.sh /path/to/erpnext_es_aeat.zip [site_name]
#
# ERPNext installs are notoriously environment-sensitive; this is a best-effort
# unattended path. If a step fails, its output points at the fix and you re-run.
set -euo pipefail

APP_ZIP="${1:?Falta la ruta al zip de la app}"
SITE="${2:-aeat.test}"
FRAPPE_USER="frappe"
BENCH_DIR="/home/${FRAPPE_USER}/frappe-bench"
DB_ROOT_PW="aeat_root_$(date +%s)"
ADMIN_PW="admin"
BRANCH="version-15"

echo "==> 1/8 Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3-dev python3-pip python3-venv python3-setuptools \
    redis-server mariadb-server libmysqlclient-dev curl xvfb libfontconfig wkhtmltopdf \
    software-properties-common build-essential

echo "==> 2/8 MariaDB (utf8mb4 + innodb)"
cat >/etc/mysql/mariadb.conf.d/99-frappe.cnf <<'CNF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
[mysql]
default-character-set = utf8mb4
CNF
systemctl restart mariadb
# set a root password (fresh installs use unix_socket; bench needs a password)
mysql -u root <<SQL || true
ALTER USER 'root'@'localhost' IDENTIFIED BY '${DB_ROOT_PW}';
FLUSH PRIVILEGES;
SQL

echo "==> 3/8 Node 18 + yarn"
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs
npm install -g yarn

echo "==> 4/8 Usuario ${FRAPPE_USER} + frappe-bench"
id -u "${FRAPPE_USER}" >/dev/null 2>&1 || useradd -m -s /bin/bash "${FRAPPE_USER}"
pip3 install --upgrade frappe-bench

echo "==> 5/8 bench init (${BRANCH})"
sudo -u "${FRAPPE_USER}" -H bash -lc "
  set -e
  cd /home/${FRAPPE_USER}
  [ -d frappe-bench ] || bench init --frappe-branch ${BRANCH} --skip-redis-config-generation frappe-bench
"

echo "==> 6/8 Site + ERPNext"
sudo -u "${FRAPPE_USER}" -H bash -lc "
  set -e
  cd ${BENCH_DIR}
  bench get-app --branch ${BRANCH} erpnext || true
  bench list-sites | grep -qx '${SITE}' || bench new-site '${SITE}' \
      --admin-password '${ADMIN_PW}' --mariadb-root-password '${DB_ROOT_PW}'
  bench --site '${SITE}' install-app erpnext
"

echo "==> 7/8 Instalar erpnext_es_aeat desde el zip"
cp "${APP_ZIP}" "/home/${FRAPPE_USER}/app.zip"
chown "${FRAPPE_USER}:${FRAPPE_USER}" "/home/${FRAPPE_USER}/app.zip"
sudo -u "${FRAPPE_USER}" -H bash -lc "
  set -e
  cd /home/${FRAPPE_USER}
  rm -rf app_src && mkdir app_src && cd app_src
  unzip -q ../app.zip
  cd ${BENCH_DIR}
  bench get-app /home/${FRAPPE_USER}/app_src/erpnext_es_aeat
  bench --site '${SITE}' install-app erpnext_es_aeat
  bench --site '${SITE}' migrate
"

echo "==> 8/8 Tests"
echo "--- regresión offline ---"
sudo -u "${FRAPPE_USER}" -H bash -lc "
  cd ${BENCH_DIR}/apps/erpnext_es_aeat && python3 regression/run_regression.py
"
echo "--- live check (dentro de ERPNext) ---"
sudo -u "${FRAPPE_USER}" -H bash -lc "
  cd ${BENCH_DIR}
  bench --site '${SITE}' execute erpnext_es_aeat.tools.live_check.run
"
echo '==> BOOTSTRAP_OK'
