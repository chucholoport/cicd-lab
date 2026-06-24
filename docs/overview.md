# cicd-lab

Solución a la prueba técnica de DevOps (3DEMAK): un stack web modular con
MySQL y Nginx como reverse proxy, un Jenkinsfile de deploy, y el
razonamiento de diagnóstico/sincronización de esquemas MySQL.

Este documento explica **por qué** se tomó cada decisión de arquitectura,
no solo qué se construyó.

## Arquitectura general

```
            ┌────────────┐
  :80 ───▶  │   proxy    │  Nginx — reverse proxy + frontend estático
            └─────┬──────┘
                   │ red "frontend"
            ┌──────┴─────┐
            │    app     │  Flask — lógica de negocio
            └─────┬──────┘
                   │ red "backend"
            ┌──────┴─────┐
            │     db     │  MySQL 8.4
            └────────────┘

            ┌────────────┐
  :8080 ──▶ │  jenkins   │  CI/CD — independiente del stack de la app
            └────────────┘
```

Cada servicio vive en su propia carpeta (`app/`, `db/`, `proxy/`,
`jenkins/`, `tests/`, `secrets/`) con su propio `Dockerfile` cuando aplica.
La idea detrás de esta separación: cada carpeta debería poder explicarse
y revisarse de forma independiente, sin tener que leer el resto del repo
para entender qué hace.

## Por qué dos redes (`frontend` / `backend`) en vez de una

`db` solo está conectado a `backend`. `proxy` solo está conectado a
`frontend`. `app` es el único servicio en ambas, porque es el único que
necesita hablar con los dos lados.

Esto significa que **`db` es inalcanzable desde `proxy`** a nivel de red,
incluso si alguien intentara saltarse la capa de aplicación. No es
seguridad perimetral real (esto sigue siendo un entorno de laboratorio),
pero refleja el principio de segmentación que se esperaría en un diseño de
producción: el servicio que recibe tráfico externo nunca debería tener
ruta directa a la base de datos.

## Por qué Docker Secrets y no variables de entorno planas

`MYSQL_PASSWORD` o `DB_PASSWORD` como variables de entorno directas
quedan visibles con `docker inspect` o leyendo `/proc/<pid>/environ` desde
el host. Los Docker secrets se montan como archivos en `/run/secrets/*`
con permisos restringidos y no aparecen en `docker inspect`.

Por eso `app` y `db` usan el patrón `*_FILE` (`DB_PASSWORD_FILE`,
`MYSQL_PASSWORD_FILE`, `MYSQL_ROOT_PASSWORD_FILE`) apuntando al path
montado, en vez de recibir el valor de la contraseña directamente.

### `.gitignore` y los archivos `.example.txt`

El primer intento de esto tuvo un bug real: `secrets/` (como entrada del
`.gitignore`, con `/` al final) le dice a git que ignore el  **directorio
completo como bloque** . Cuando git hace eso, nunca llega a evaluar
archivo por archivo lo que hay dentro — así que cualquier regla de
excepción (`!secrets/algo`) quedaba sin efecto.

El fix fue ignorar el **contenido** (`secrets/*`) en vez del directorio, y
recién ahí las excepciones (`!secrets/*.example.txt`) empezaron a
funcionar. Resultado:

* `secrets/db_password.example.txt`, `secrets/db_root_password.example.txt`
  → **sí** se versionan, son plantillas con valores placeholder
  (`CHANGE_ME_...`), nunca contraseñas reales.
* `secrets/db_password.txt`, `secrets/db_root_password.txt` (los reales)
  → ignorados explícitamente, se crean en local copiando los `.example.txt`
  y nunca llegan al repo.

En un pipeline real (Jenkins/GitLab), estos valores ni siquiera vivirían
como archivos en el repo — vendrían del credentials store o de variables
de CI/CD inyectadas en tiempo de deploy. El patrón de archivo es
específicamente para que `docker compose up` funcione en local/dev.

## Por qué el proxy se construye con `build` y no con `image` + volúmenes

La primera versión montaba `nginx.conf` y `conf.d/` como bind-mounts sobre
la imagen oficial `nginx:alpine`, mientras el `Dockerfile` del proxy (que
ya hacía `COPY` de esos mismos archivos) quedaba sin usarse — dos formas
de lograr lo mismo, compitiendo, y solo una real. Se unificó a `build`
para que la imagen del proxy sea autocontenida y versionada: lo que se
construye en CI es exactamente lo que corre en producción, sin depender de
que el filesystem del host tenga los archivos correctos en la ruta
correcta.

## Por qué el frontend vive en `proxy/html/` y no en un servicio aparte

Nginx ya está ahí, ya sirve tráfico en el puerto 80, y servir archivos
estáticos es literalmente lo que Nginx hace mejor — añadir un cuarto
contenedor solo para servir 3 archivos (`index.html`, `app.js`,
`style.css`) sería sobre-ingeniería para lo que pide este ejercicio.

El `Dockerfile` del proxy copia `html/` a `/usr/share/nginx/html/` en
build-time, y `app.conf` expone esos archivos bajo `/app/` usando `alias`
(no `root` — con `alias` el prefijo del `location` se descarta al
resolver la ruta física, así no hace falta duplicar la estructura de
carpetas dentro de la imagen).

### Por qué `/api/` como prefijo, sin tocar las rutas de Flask

El frontend (`app.js`) necesitaba pedir datos a algún lado, pero Flask ya
tenía `/` y `/health` funcionando y no había razón para renombrarlas. La
solución fue resolverlo enteramente en Nginx:

```nginx
location /api/ {
    proxy_pass http://python_app/;   # la "/" final es la parte clave
    ...
}
```

El `/` al final de `proxy_pass` hace que Nginx **recorte** el prefijo
`/api` antes de reenviar la petición — `/api/` le llega a Flask como `/`,
sin que `main.py` necesite saber que existe un prefijo. Sin esa barra
final, Flask recibiría literalmente `/api/`, que no existe, y respondería
404.

## Por qué `tests/` es una carpeta separada (y no vive dentro de `app/`)

Pytest necesita poder importar `src.main` para probarlo, pero las pruebas
en sí no son parte de la aplicación que corre en producción — son
herramienta de validación, con su propio ciclo de vida y dependencias
(`pytest`, mocks). Separarlas en su propia carpeta en la raíz del repo
modulariza esa responsabilidad: `app/` es "lo que se despliega",
`tests/` es "lo que valida que lo desplegado funciona".

Esa separación impactó directamente dos archivos:

* **`app/Dockerfile`** : el `context` del build de `app` pasó de
  `./app` a `.` (la raíz del repo), porque para que el Dockerfile pueda
  copiar `tests/` dentro de la imagen necesita ver más allá de la carpeta
  `app/`. Sin ese cambio de contexto, Docker no tiene acceso a archivos
  fuera del directorio que se le pasó como contexto de build.
* **`docker-compose.yml`** : el servicio `app` ahora declara
  `build.context: .` y `build.dockerfile: app/Dockerfile` por separado,
  en vez del `context: ./app` original.

`tests/conftest.py` mockea la conexión a MySQL y la lectura de secrets
(`read_secret`), para que la suite de pruebas no dependa de que exista una
base de datos real corriendo — esto es lo que permite que Jenkins corra
`pytest` dentro del contenedor recién construido, en el stage de Test,
sin necesitar levantar todo el stack de Compose primero.

## Por qué se integró Jenkins al `docker-compose.yml` (aunque no esté 100% funcional)

La idea no era tener un Jenkins productivo corriendo de fondo, sino dejar
la **infraestructura como código** para el pipeline, de modo que el
`Jenkinsfile` (`jenkins/jobs/daily.jenkinsfile`) no sea un archivo
aislado y teórico, sino algo que corre contra un Jenkins real con acceso
real al daemon de Docker del host — el patrón "Docker outside of Docker":

* `jenkins/Dockerfile` parte de la imagen oficial LTS y le instala el
  cliente de Docker (`docker.io`).
* El contenedor monta `/var/run/docker.sock` del host y se agrega al grupo
  `${DOCKER_GID}`, para poder ejecutar `docker build`/`docker run` desde
  dentro de Jenkins, usando el mismo daemon que ya tiene el host —  en vez
  de levantar Docker-in-Docker (más pesado y con más fricción de
  permisos).
* Vive en ambas redes (`frontend`/`backend`) porque necesita poder
  construir y probar la imagen de `app`, que a su vez necesita poder
  alcanzar `db` durante el stage de Test.

Lo que falta para que esté 100% funcional es justamente lo que el
ejercicio no pedía automatizar: credenciales reales de un registry, un
servidor de staging/producción real, y la configuración inicial de
Jenkins (crear el job, instalar plugins). La intención de incluirlo en
Compose era demostrar que el pipeline no es un documento aparte, sino
parte de la misma arquitectura versionada — "pipelines as code" en el
sentido literal: el propio Jenkins también se construye desde un
Dockerfile en el repo.

## Resumen de decisiones (tabla rápida)

| Decisión                                       | Alternativa descartada               | Por qué                                                                              |
| ----------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------------- |
| Dos redes (`frontend`/`backend`)            | Una sola red plana                   | `db`no debe ser alcanzable desde `proxy`                                          |
| Docker secrets vía archivo                     | Env vars planas                      | No quedan expuestas en `docker inspect`                                             |
| `secrets/*`en `.gitignore`(no `secrets/`) | Ignorar la carpeta completa          | Ignorar el directorio bloquea la evaluación de excepciones `!`                     |
| Proxy con `build`                             | `image: nginx:alpine`+ bind-mounts | Imagen autocontenida y versionada, sin código muerto (el Dockerfile sí se usa)      |
| Frontend dentro de `proxy/html/`              | Servicio frontend aparte             | Nginx ya sirve estáticos de forma nativa; un 4° contenedor sería sobre-ingeniería |
| `/api/`resuelto solo en Nginx                 | Renombrar rutas en Flask             | Cero acoplamiento entre el frontend y la implementación interna de la API            |
| `tests/`separado en la raíz                  | Pruebas dentro de `app/`           | Separa "lo que se despliega" de "lo que valida el despliegue"                         |
| Jenkins con Docker socket montado               | Docker-in-Docker                     | Mismo daemon que el host, menos overhead y menos problemas de permisos                |
