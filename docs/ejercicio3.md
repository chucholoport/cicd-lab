# Base de Datos MySQL: Diagnóstico y Sincronización de Esquemas

### ⏱  ~20 minutos  ·  Entregable: comandos SQL y razonamiento escrito

Este ejercicio tiene dos partes independientes. Puedes elegir el orden. Para cada una, escribe los comandos que usarías y explica brevemente tu razonamiento.

**Lo que debe incluir tu entregable:**

* **Parte A — Restaurar dump con tabla faltante:** Te dan un dump de MySQL de 2GB. Lo restauras con: `mysql -u root -p staging_db < dump.sql` — termina sin errores. Pero la app lanza: `Table 'staging_db.user_sessions' doesn't exist`. Escribe los comandos para diagnosticar qué pasó y cómo resolverías el problema.
* **Parte B — Sincronizar esquema entre ambientes:** En Dev se agregaron dos columnas a la tabla orders: `discount_code VARCHAR(50)` y `fulfilled_at DATETIME`. Producción no las tiene todavía. Escribe los comandos SQL para sincronizar el esquema de forma segura, sin perder datos existentes en Producción.

> Nota: Para este ejercicio no hay una respuesta única. Lo que evaluamos es tu razonamiento: cómo lees el problema, qué comandos propones y por qué, y si consideras los riesgos antes de actuar.

---

# RESPUESTAS

## A. Tabla faltante después de restaurar dump

### Anotaciones

Si bien mi principal experiencia no es el manejo directo de bases de datos SQL, este tipo de problemas puede analizarse con una metodología similar a la que se utiliza en debugging de sistemas: verificación incremental del estado del sistema y validación de consistencia entre lo esperado y lo realmente desplegado.

En este caso, el primer paso es confirmar la existencia de la base de datos y listar sus tablas, para validar que el restore del dump haya generado correctamente el esquema esperado. Posteriormente, se verifica específicamente la existencia de la tabla afectada (user_sessions) para aislar si el problema es puntual o sistémico dentro del restore.

A continuación, se analiza el contenido del dump o del proceso de restauración para confirmar si la tabla fue incluida originalmente o si se omitió por un dump parcial, un error de exportación o por dependencias de orden de creación. Finalmente, si no se identifica un problema evidente en el dump, se revisan los logs del proceso de importación para detectar errores silenciosos durante la carga, como conflictos de foreign keys, errores de sintaxis o interrupciones parciales del restore.

Este enfoque permite distinguir entre un problema de datos faltantes en origen versus un fallo en el proceso de restauración, lo cual es equivalente a validar consistencia entre el estado esperado del sistema y su estado real post-deploy.

### Diagnóstico

1. Verificar si la base existe y contiene la tabla:

```bash
mysql -u root -p -e "USE staging_db; SHOW TABLES;"
```

2. Confirmar si la tabla específica existe:

```bash
mysql -u root -p -e "USE staging_db; SHOW TABLES LIKE 'user_sessions';"
```

3. Inspeccionar si el dump contiene la tabla:

```bash
grep -n "user_sessions" dump.sql
```

4. Buscar errores durante importación (re-ejecutar con logging):

```bash
mysql -u root -p staging_db < dump.sql 2> import_errors.log
```

---

### Posibles causas

* El dump fue generado sin esa tabla (dump parcial o filtrado).
* La tabla pertenece a otro esquema no incluido.
* Error silencioso durante import (foreign keys / order de creación).
* La tabla se crea en otro script post-dump (migrations no ejecutadas).

---

### Resolución

**Caso 1: falta en el dump**

```bash
mysqldump -u root -p staging_db user_sessions > user_sessions.sql
mysql -u root -p staging_db < user_sessions.sql
```

**Caso 2: la tabla debería crearse por migración**

```bash
# ejecutar migraciones pendientes (ejemplo conceptual)
flask db upgrade
# o
alembic upgrade head
```

**Caso 3: restauración completa corregida**

```bash
mysql -u root -p staging_db < full_dump_fixed.sql
```

---

# B. Sincronización de esquema (Dev → Producción)

A partir de experiencia previa en sistemas embebidos, este tipo de problema puede interpretarse de forma análoga al proceso de actualización por etapas de un sistema flash: primero se actualiza el bootloader, posteriormente el firmware base, luego la aplicación principal y finalmente capas adicionales del sistema. Este orden es importante porque cada capa depende de la compatibilidad de la anterior para garantizar estabilidad del sistema completo.

De forma equivalente, en bases de datos distribuidas entre ambientes (Dev y Producción), los cambios de esquema deben aplicarse de manera incremental y compatible hacia atrás. En este caso, Dev ya contiene nuevas columnas (discount_code y fulfilled_at), mientras que Producción aún no, lo que indica una desincronización de esquema entre entornos.

La forma segura de resolverlo es aplicar una migración no destructiva en Producción, extendiendo el esquema sin afectar los datos existentes. Esto equivale a introducir nuevas “capas” sin modificar las estructuras base ya utilizadas por el sistema en ejecución.

El cambio puede realizarse mediante:

```sql
ALTER TABLE orders
ADD COLUMN discount_code VARCHAR(50) NULL,
ADD COLUMN fulfilled_at DATETIME NULL;
```

ALTER TABLE orders
ADD COLUMN discount_code VARCHAR(50) NULL,
ADD COLUMN fulfilled_at DATETIME NULL;

El uso de columnas NULL permite mantener compatibilidad con registros existentes, evitando fallos en la aplicación durante el despliegue. Posteriormente, si es necesario, se puede realizar un backfill controlado de datos o aplicar restricciones adicionales una vez que el sistema ya opera con el nuevo esquema.

Este enfoque garantiza compatibilidad progresiva entre entornos, similar a un proceso de actualización por etapas en sistemas embebidos donde no es posible sobrescribir completamente el sistema sin respetar dependencias entre capas.