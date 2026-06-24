# cicd-lab

Stack web modular de ejemplo con Flask, MySQL y Nginx como reverse proxy,
más un pipeline de CI/CD con Jenkins. Construido como prueba técnica de
DevOps (3DEMAK).

Para el razonamiento detrás de cada decisión de arquitectura, ver
[`docs/overview.md`](./docs/overview.md).

## Qué incluye

* **App web** (Flask) con healthcheck y verificación de conectividad a MySQL.
* **Base de datos MySQL** con esquema inicial autoaplicado y persistencia
  en volumen.
* **Nginx** como reverse proxy + servidor del frontend estático.
* **Frontend** simple (HTML/JS) que consume la API y muestra su estado.
* **Jenkins** containerizado con un pipeline de ejemplo (build → test →
  push → deploy a staging → aprobación manual → deploy a producción).
* **Suite de pruebas** con pytest para la app.
* **Secrets** manejados como archivos (Docker secrets), nunca como
  variables de entorno planas ni commiteados en git.

## Cómo levantarlo

```bash
# 1. Crear los secrets reales a partir de las plantillas
cp secrets/db_password.example.txt secrets/db_password.txt
cp secrets/db_root_password.example.txt secrets/db_root_password.txt
# editar ambos archivos con contraseñas reales y distintas entre sí

# 2. Levantar el stack
docker compose up --build
```

Servicios disponibles una vez arriba:

| URL                         | Qué muestra                |
| --------------------------- | --------------------------- |
| `http://localhost/`       | Redirige al dashboard       |
| `http://localhost/app/`   | Frontend (dashboard)        |
| `http://localhost/api/`   | JSON de estado de la app/DB |
| `http://localhost/health` | Healthcheck de la app       |
| `http://localhost:8080`   | Jenkins                     |

## Estructura del proyecto

```
.
├── app/        # Aplicación Flask
├── db/         # Esquema inicial de MySQL
├── proxy/      # Nginx: reverse proxy + frontend estático
├── jenkins/    # Imagen y pipeline de CI/CD
├── tests/      # Pruebas pytest de la app
├── secrets/    # Plantillas de credenciales (valores reales gitignored)
└── docs/       # Documentación extendida
```

### `app/`

Aplicación Flask mínima que expone dos rutas:

* `/` — verifica conectividad a MySQL y devuelve un JSON con el estado de
  la app y de la base de datos.
* `/health` — healthcheck simple, usado por Docker y por Nginx.

Lee la contraseña de la base de datos desde un Docker secret montado en
`/run/secrets/db_password`, no desde una variable de entorno directa.

### `db/`

Imagen oficial de `mysql:8.4`. El script en `db/init/` se ejecuta
automáticamente la primera vez que el contenedor arranca (vía
`docker-entrypoint-initdb.d`), creando la base, el esquema y una fila de
prueba. Los datos persisten en un volumen nombrado, así que sobreviven a
un restart del contenedor.

### `proxy/`

Nginx hace dos trabajos en este proyecto:

1. **Reverse proxy** : recibe todo el tráfico en el puerto 80 y lo enruta
   hacia la app Flask bajo el prefijo `/api/`.
2. **Servidor de archivos estáticos** : sirve el frontend (`proxy/html/`)
   bajo `/app/`.

### `proxy/html/`

Frontend estático muy simple: un dashboard que hace `fetch` al endpoint
`/api/` y muestra la respuesta en pantalla, con un botón para refrescar.
Sin frameworks ni build step — HTML, CSS y JS plano.

### `jenkins/`

Imagen de Jenkins LTS con el cliente de Docker instalado, para poder
construir y correr contenedores desde dentro del propio pipeline
(montando el socket de Docker del host). El job de ejemplo
(`jenkins/jobs/daily.jenkinsfile`) define las etapas de un deploy típico:
build de la imagen, pruebas, push a un registry, deploy a staging,
aprobación manual, y deploy a producción.

### `tests/`

Pruebas con pytest para la app Flask. Usan mocks para la conexión a MySQL
y la lectura de secrets, así que corren de forma aislada sin necesitar el
resto del stack levantado — esto es lo que permite que Jenkins las
ejecute dentro del contenedor recién construido, en el stage de Test.

### `secrets/`

Solo contiene plantillas (`*.example.txt`) con valores placeholder. Los
archivos reales (`db_password.txt`, `db_root_password.txt`) se generan
localmente a partir de esas plantillas y están excluidos de git.

### `docs/`

Documentación adicional. `overview.md` explica el razonamiento detrás de
cada decisión de arquitectura tomada en el proyecto, así como las 
respuestas del ejercicio 3.
