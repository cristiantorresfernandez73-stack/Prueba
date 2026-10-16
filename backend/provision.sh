#!/usr/bin/env bash
set -euo pipefail

app_user="SSH"
app_dir="/home/${app_user}/tft-backend/backend"
env_file="${app_dir}/.env"
schema_file="${app_dir}/schema.sql"
service_template="${app_dir}/deploy/tft-meta-api.service"
mysql_admin_user="${MYSQL_ADMIN_USER:-root}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root: sudo bash provision.sh" >&2
  exit 1
fi

if [[ -e "${env_file}" ]]; then
  echo "Refusing to overwrite ${env_file}; preserve and review existing credentials first." >&2
  exit 1
fi

if [[ ! -x "${app_dir}/.venv/bin/uvicorn" || ! -f "${schema_file}" || ! -f "${service_template}" ]]; then
  echo "Backend files or virtual environment are missing from ${app_dir}." >&2
  exit 1
fi

if ! systemctl is-active --quiet mysql; then
  echo "MySQL is not running; start and verify it before provisioning." >&2
  exit 1
fi

db_password="$(python3 -c 'import secrets, string; parts=[secrets.choice(string.ascii_lowercase), secrets.choice(string.ascii_uppercase), secrets.choice(string.digits), secrets.choice("!@#%_-+")]; alphabet=string.ascii_letters+string.digits+"!@#%_-+"; parts.extend(secrets.choice(alphabet) for _ in range(44)); secrets.SystemRandom().shuffle(parts); print("".join(parts))')"
admin_token="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

mysql --protocol=socket --user="${mysql_admin_user}" --password < "${schema_file}"
mysql --protocol=socket --user="${mysql_admin_user}" --password <<SQL
CREATE USER IF NOT EXISTS 'tft_api'@'127.0.0.1' IDENTIFIED BY '${db_password}';
ALTER USER 'tft_api'@'127.0.0.1' IDENTIFIED BY '${db_password}';
GRANT SELECT, INSERT ON tft_meta.meta_snapshots TO 'tft_api'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

install -o "${app_user}" -g "${app_user}" -m 0600 /dev/null "${env_file}"
printf '%s\n' \
  'DB_HOST=127.0.0.1' \
  'DB_PORT=3306' \
  'DB_NAME=tft_meta' \
  'DB_USER=tft_api' \
  "DB_PASSWORD=${db_password}" \
  "ADMIN_TOKEN=${admin_token}" \
  'CORS_ORIGINS=http://localhost:5500,http://127.0.0.1:5500' > "${env_file}"

install -o root -g root -m 0644 "${service_template}" /etc/systemd/system/tft-meta-api.service
systemctl daemon-reload
systemctl enable --now tft-meta-api.service
systemctl is-active --quiet tft-meta-api.service

echo "MySQL schema and least-privilege API account are configured."
echo "The API is active on 127.0.0.1:8000. Secrets are stored in ${env_file} (mode 0600) and were not printed."