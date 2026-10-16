# Nexo TFT

Guía estática en español para Teamfight Tactics. No requiere instalación, compilación ni servidor propio. Las páginas se pueden publicar tal cual en GitHub Pages, Netlify o cualquier hosting estático.

## Vista previa

Abre `index.html` en un navegador. La guía y los datos de temporada también funcionan desde `file://`; las fuentes tipográficas externas requieren conexión a Internet.

## Actualizar el set y el ranking

Edita `season-data.js` al cambiar el set, parche, región o rango:

- `season`, `patch`, `region` y `rank` describen el filtro de OP.GG usado.
- `checkedAt` es la fecha en la que se copiaron las estadísticas.
- `compositions` admite entre 10 y 100 builds ordenadas por `firstRate`, con las métricas mostradas en la tabla.
- `source` apunta al ranking de OP.GG ordenado por tasa de primer puesto.

La página genera la tabla desde ese archivo y permite buscar por nombre, filtrar por tier/categoría y cambiar el orden. La tabla y la API admiten hasta 100 builds. En la consulta de OP.GG usada para el snapshot del 2 de octubre de 2026 solo se publicaron 50 composiciones estándar; esos son los datos que muestra ahora Nexo TFT, sin rellenar los puestos restantes con cifras inventadas. OP.GG bloquea la inserción de su web en otras páginas y no se ha confirmado una API pública para estadísticas, así que el snapshot se actualiza al importar datos autorizados. El enlace «Ver ranking en vivo» abre el ranking vigente en OP.GG.

## Publicar

Sube todos los archivos de la carpeta a un repositorio y activa GitHub Pages para la rama/carpeta raíz, o publica la carpeta raíz en Netlify. No añadas claves API al código del navegador. Para obtener sincronización automática de estadísticas hará falta un proveedor con API autorizada y, si requiere credenciales, un backend o función serverless que las mantenga privadas.

## Backend MySQL

El backend vive en `backend/`. Mantén MySQL en `localhost`; no abras el puerto 3306 a Internet.

1. En Debian con Python 3.13, instala el soporte para entornos virtuales: `sudo apt update` y `sudo apt install python3.13-venv`.
2. Como usuario `SSH`, desde `backend/`, crea el entorno virtual e instala las dependencias:

	```sh
	python3 -m venv .venv
	. .venv/bin/activate
	pip install -r requirements.txt
	```

3. Cuando MySQL esté activo y `.venv` contenga Uvicorn, ejecuta `sudo bash provision.sh` desde `backend/`. El script pedirá la contraseña del administrador MySQL en el prompt seguro del cliente; no la escribas en el chat. Genera otras credenciales aleatorias sin imprimirlas, crea el esquema y un usuario local con permisos mínimos, guarda `.env` con modo `0600` y activa el servicio systemd en `127.0.0.1:8000`. Se niega a sobrescribir un `.env` existente.
4. Copia los archivos estáticos al directorio `/home/SSH/tft-backend/site/` y ejecuta `sudo bash backend/deploy/publish-site.sh` desde el repositorio del backend. El script instala Nginx si hace falta, sirve la web en `http://192.168.1.41`, configura el proxy `/api/` y bloquea el endpoint administrativo desde la red.
5. Para publicarla fuera de la LAN, usa un dominio con DNS hacia una IP pública, cambia `server_name` en `backend/deploy/nginx-tft-guide.conf`, configura HTTPS y revisa el firewall/router antes de abrir los puertos 80/443. No expongas MySQL ni el endpoint administrador.
6. Publica un snapshot con `POST /api/v1/admin/meta` y la cabecera `Authorization: Bearer <ADMIN_TOKEN>`. Envía entre 10 y 100 builds con `name`, `tier`, `category`, `firstRate`, `top4Rate`, `avgPlace` y `pickRate`, además de `season`, `patch`, `region`, `rank`, `checkedAt` (AAAA-MM-DD) y `source` (URL HTTP/HTTPS). La API las guarda ordenadas por tasa de primer puesto.

`GET /api/health` comprueba la conexión a MySQL. El endpoint público `GET /api/v1/meta/current` sirve el snapshot más reciente. A falta de una fuente de datos automática autorizada, un operador debe importar cada snapshot nuevo; la web conserva el snapshot local como respaldo.