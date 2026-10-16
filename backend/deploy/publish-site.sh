#!/usr/bin/env bash
set -euo pipefail

app_user="SSH"
site_dir="/home/${app_user}/tft-backend/site"
web_root="/var/www/tft-guide"
nginx_available="/etc/nginx/sites-available/tft-guide"
nginx_enabled="/etc/nginx/sites-enabled/tft-guide"
nginx_template="/home/${app_user}/tft-backend/backend/deploy/nginx-tft-guide.conf"
marker="${web_root}/.tablero-tactico-managed"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root: sudo bash publish-site.sh" >&2
  exit 1
fi

if [[ ! -f "${site_dir}/index.html" || ! -f "${site_dir}/styles.css" || ! -f "${nginx_template}" ]]; then
  echo "Website files or the Nginx template are missing." >&2
  exit 1
fi

if [[ ! -x "$(command -v nginx || true)" ]]; then
  apt-get install -y nginx
fi

if [[ -d "${web_root}" && ! -f "${marker}" ]] && [[ -n "$(find "${web_root}" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  echo "${web_root} is not empty and is not managed by this publisher; refusing to overwrite it." >&2
  exit 1
fi

install -d -o root -g www-data -m 0755 "${web_root}"
cp -a "${site_dir}/." "${web_root}/"
touch "${marker}"
chown -R root:www-data "${web_root}"
find "${web_root}" -type d -exec chmod 0755 {} +
find "${web_root}" -type f -exec chmod 0644 {} +

install -o root -g root -m 0644 "${nginx_template}" "${nginx_available}"
ln -sfn "${nginx_available}" "${nginx_enabled}"
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "Website published at http://192.168.1.41"
echo "The admin API route is blocked in Nginx; manage snapshots over SSH/local access."