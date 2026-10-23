## API de TradConnect

Esta API está diseñada para gestionar compra y venta de productos. Desarrollada con Django y Django REST Framework, incluye autenticación JWT, documentación Swagger, y conexión a SQL Server.

## Tecnologías utilizadas

- Python 3.13+
- Django  
- Django REST Framework  
- SQL Server  
- JWT (Json Web Token)  
- Swagger (drf-yasg)  
- Apidog / Postman (para pruebas)

## Instalación

Clona el repositorio:
```bash
https://github.com/wil138/TradConnect/
cd TradConnect
```
# Instala dependencias:
```python
- pip install -r requirements.txt
```

# Configura la base de datos en settings.py
Configuración de base de datos (SQL Server)
un ejemplo para SQL Server usando `pyodbc`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sql_server.pyodbc',
        'NAME': 'NombreBD',
        'USER': 'usuario',
        'PASSWORD': 'contraseña',
        'HOST': 'localhost',
        'PORT': '1433',
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'trusted_connection': 'yes',
        },
    }
}
```

## Preparar conexión a MongoDB

### Colecciones NoSQL del negocio

Los esquemas Pydantic Create/Read están en `Tradconnect_no_sql/models.py`.
Se conservan las 13 colecciones del modelo documental: usuarios, empresas y roles;
preferencias de negocio, categorías, productos y métodos de pago; evaluaciones;
transacciones no exitosas y sustituciones; incidencias y evidencias; comentarios e
interacciones; y necesidades no satisfechas.

Las rutas SQL y el login JWT existentes siguen bajo `/api/`. No se cambia la
fuente de autenticación: guardar un usuario en MongoDB no crea un usuario SQL.
Las nuevas rutas documentales requieren JWT de un usuario SQL con rol `Admin`
o `Administrador`, porque gestionan información de varias empresas. Esta versión
no habilita acceso directo para clientes/proveedores; requiere definir sus permisos
por empresa antes de abrir esas rutas.

```text
GET, POST                 /api/nosql/preferencias_negocio/
GET, PUT, PATCH, DELETE    /api/nosql/preferencias_negocio/<id>/
GET, POST                 /api/nosql/usuarios_empresas_roles/
```

El mismo patrón funciona con el nombre de cualquiera de las 13 colecciones.
POST genera `_id` automáticamente (`uer_<uuid>` para usuarios). PUT reemplaza el
contenido; PATCH valida el documento completo tras combinar cambios. Las listas
admiten `limit=100&offset=0`, máximo 500, y devuelven `results`, `limit`, `offset`.
Las respuestas nunca incluyen `password_hash`. Las escrituras de usuario exigen
un hash reconocido por Django; no envíes contraseñas en texto plano.

Las referencias `*_id_sql` se comprueban en SQL. Las referencias a preferencias,
transacciones, incidencias y comentarios se comprueban en MongoDB; no se permite
borrar un documento que tenga esos dependientes. Los IDs `usuario_id` y
`empresa_id` son cadenas: la carga SQL usa el ID SQL convertido a texto. No hay
sincronización automática de estas 13 colecciones ni transacciones distribuidas entre ambas bases;
las validaciones no sustituyen la consistencia ante escrituras concurrentes.
Fechas y decimales se almacenan como ISO 8601 y cadenas decimales respectivamente.

### Carga de datos

Configura MongoDB y SQL Server antes de ejecutar:

```powershell
python manage.py cargar_usuarios_nosql --validar
python manage.py cargar_usuarios_nosql
python manage.py cargar_documentos_nosql Tradconnect_no_sql/fixtures/ejemplo.json --validar
python manage.py cargar_documentos_nosql Tradconnect_no_sql/fixtures/ejemplo.json
```

El archivo de ejemplo es una plantilla para desarrollo. Ajusta los IDs SQL de
categoría, producto, método de pago y pedido a registros existentes, así como los
IDs de empresas/usuarios y sus nombres. No se ejecuta automáticamente. El JSON
usa `{ "coleccion": [{ "_id": "identificador-estable", ...campos }] }`.
El importador valida el archivo completo antes de escribir; `--validar` no escribe.
Los IDs son obligatorios en archivos para que repetir la carga actualice sin
duplicar. Los lotes no son atómicos entre colecciones: si falla una escritura,
repite el archivo para completar la carga. No elimina documentos ausentes del JSON.

La carga de usuarios combina `Usuario`, `Empresa` y `Rol` de SQL, un vínculo por
usuario/empresa con ID `uer_sql_<usuario>_<empresa>`. Traduce Restaurante a Cliente;
Proveedor permanece Proveedor; Admin/Administrador a Administrador. Como SQL no
tiene estado de usuario ni fecha de asignación separados, usa `True` y la fecha
de registro; el estado del vínculo procede del estado de la empresa. No asocia
una sucursal arbitraria. Rechaza roles sin equivalencia, empresas incompletas y
contraseñas sin hash reconocido. Puede completar algunos vínculos antes de fallar;
es repetible y `--validar` permite detectar errores antes de escribir.

Los catálogos de enumeraciones no venían en el fragmento: los valores provisionales
están centralizados en `models.py`: TipoEmpresa (Restaurante, Proveedor, Interna),
NombreRol (Cliente, Proveedor, Administrador), EstadoIncidencia (Pendiente,
En proceso, Resuelta) y EstadoNecesidad (Pendiente, En proceso, Satisfecha).
Confírmalos antes de usar datos reales.

La carga genérica anterior `python manage.py cargar_nosql` se conserva como
compatibilidad para proyecciones SQL de solo lectura (por ejemplo,
`/api/nosql/producto/`); no carga estas 13 colecciones ni copia usuarios.
Pruebas: `python manage.py test Tradconnect_no_sql`.

### Auditoría de claves sin escrituras

```powershell
python manage.py auditar_bases --limite-ids 0
# Opcional: mostrar hasta 20 IDs por tipo de diferencia
python manage.py auditar_bases --limite-ids 20
```

Este comando consulta ambas bases reales cuando se ejecuta; no carga ni corrige
datos. Devuelve JSON con cantidades e IDs faltantes/sobrantes y vínculos distintos
para `pedido`, `detallepedido`, `historialestadopedido`, `empresa`, `rol` y
`pedidos_web`. Comprueba también IDs anidados de detalles e historial, duplicados
y estructuras incompletas de la proyección web. Para `usuarios_empresas_roles`
reproduce las claves deterministas y traducciones del cargador SQL, incluyendo
usuarios con varias empresas o sin empresa, y reporta roles sin equivalencia.
Las empresas/roles SQL sin vínculos de usuario no se equiparan al número de
documentos: un usuario puede tener varios vínculos.

Todas las consultas seleccionan campos explícitos: IDs, vínculos y nombres de
roles; no consultan contraseñas, hashes, correos, nombres personales ni importes.
`--limite-ids 0` omite las muestras de IDs. El código de salida es distinto de cero
si hay diferencias o si la comparación no pudo completarse. Una colección no
cargada aparecerá como faltante; el comando no la crea ni la rellena.

Es una auditoría de claves y relaciones, no de igualdad completa de contenidos:
no verifica importes, fechas ni valores inferidos como `estado_usuario`. Tampoco
es una instantánea distribuida: evita escrituras concurrentes para obtener una
comparación estable. Mantiene mapas de claves en memoria. La comprobación más
amplia de contenido de pedidos sigue disponible en `sincronizar_pedidos --verificar`.

### Funcionamiento de la sincronización de pedidos

Con `MONGODB_URI` configurada, los cambios ORM en `Pedido`, `Detallepedido` e
`Historialestadopedido` se sincronizan después del commit SQL. Un rollback
descarta sus callbacks. Se actualizan `pedido`, `detallepedido`,
`historialestadopedido` y `pedidos_web`. Esta última proyección contiene el formato
de `PedidoSerializer`, detalles e `historial`, y se publica completa al final.
Se eliminan detalles e historial que ya no pertenecen al pedido; eliminar un
pedido SQL también elimina sus cuatro proyecciones.

Las rutas `/api/pedidos/` siguen usando SQL. La web puede consultar Mongo con el
JWT actual de cualquier usuario autenticado:

```text
GET /api/nosql/mis-pedidos/?limit=100&offset=0
GET /api/nosql/mis-pedidos/123/
```

Filtran por todas las empresas del usuario como comprador o proveedor. Un pedido
de otra empresa devuelve 404. No aceptan una empresa del cliente para ampliar
el acceso. El listado usa `results`, `limit` y `offset`. Mongo inaccesible devuelve
503; ejecuta la carga inicial antes de usar estas rutas.

`POST /api/auth/dump-all/` conserva `username`, `password`, tokens y datos agrupados.
Por defecto consulta pedidos SQL. Agrega `"fuente_pedidos": "mongo"` para usar Mongo
en los pedidos. Se conserva el alcance de la primera empresa del usuario que ya
tenía ese endpoint. Catálogos y estadísticas siguen en SQL. Los nuevos GET con
JWT no generan tokens adicionales.

```powershell
python manage.py sincronizar_pedidos
python manage.py sincronizar_pedidos --verificar
python manage.py sincronizar_pedidos --pedido 123
python manage.py sincronizar_pedidos --limpiar
```

`--verificar` no escribe: compara contenido de las cuatro proyecciones por pedido,
reporta diferencias y devuelve error si las encuentra. En la comprobación completa
muestra cantidades SQL/Mongo de las tres colecciones fuente. `--limpiar` incluye
y elimina proyecciones de pedidos ausentes en SQL. Las recargas usan upsert por ID:
se pueden repetir tras fallos parciales. Verifica sin escrituras concurrentes
para comparar una foto estable.

La sincronización automática se ejecuta dentro del proceso después del commit;
no es una cola persistente y puede añadir latencia. Si falla, SQL conserva el
pedido, se registra su ID y se recupera con el comando. Una caída del proceso
entre commit y sincronización también requiere recarga. SQL directo,
`QuerySet.update()` y `bulk_create()` no emiten señales: recarga después de usarlos.
Los nombres y catálogos incrustados se actualizan al sincronizar el pedido.
Sin URI MongoDB la API SQL sigue funcionando.

MongoDB se configura por separado de `DATABASES`, que sigue usando SQL Server.
La aplicación obtiene la URI y el nombre de la base desde variables de entorno:

```powershell
$env:MONGODB_URI = "mongodb://localhost:27017"
$env:MONGODB_DATABASE = "tradconnect"
```

Configura `MONGODB_URI` en el entorno de despliegue y no guardes credenciales en el
código. Cuando la integración use MongoDB, importa `database` desde
`config.mongodb`; el cliente PyMongo se reutiliza durante el proceso. Esta
preparación no migra `Usuario`, `Rol` ni `Empresa`, ni modifica sus referencias
SQL.

# Ejecuta migraciones:
```python
- python manage.py makemigrations
- python manage.py migrate
```
# Inicia el servidor:
```python
- python manage.py runserver
```
# Autenticación
La API utiliza JWT. Para obtener un token:
```python
- POST /api/token/ → Enviar usuario y contraseña
- POST /api/token/refresh/ → Refrescar token
```

Incluye el token en el encabezado:
- Authorization: Bearer <tu_token>

# Accedé a la documentación de la api Swagger en:
[http://localhost:8000/swagger/

## Endpoints principales
| Tabla / Recurso     | Ruta base                                           | Métodos disponibles              | Descripción general                          |
|---------------------|-----------------------------------------------------|----------------------------------|----------------------------------------------|
| Usuario             | http://127.0.0.1:8000/api/TradConnect/usuarios/          | GET, POST, PUT, DELETE           | Gestión de usuarios del sistema              |
| Cliente             | http://127.0.0.1:8000/api/TradConnect/clientes/          | GET, POST, PUT, DELETE           | Registro y administración de clientes        |
| Proveedor           | http://127.0.0.1:8000/api/TradConnect/proveedores/       | GET, POST, PUT, DELETE           | Gestión de proveedores y sus productos       |
| Establecimiento     | http://127.0.0.1:8000/api/TradConnect/establecimientos/  | GET, POST, PUT, DELETE           | Información de locales físicos o virtuales   |
| Productos           | http://127.0.0.1:8000/api/TradConnect/productos/         | GET, POST, PUT, DELETE           | Catálogo de productos disponibles            |
| Pedido              | http://127.0.0.1:8000/api/TradConnect/pedidos/           | GET, POST, PUT, DELETE           | Registro y seguimiento de pedidos            |
| Factura             | http://127.0.0.1:8000/api/TradConnect/facturas/          | GET, POST, PUT, DELETE           | Generación y consulta de facturas            |
| EstadoProducto      | http://127.0.0.1:8000/api/TradConnect/estado-producto/   | GET, POST, PUT, DELETE           | Estado actual de productos (activo, agotado) |
| EstadoPedido        | http://127.0.0.1:8000/api/TradConnect/estado-pedido/     | GET, POST, PUT, DELETE           | Estado del pedido (pendiente, entregado)     |
| MetodoPago          | http://127.0.0.1:8000/api/TradConnect/metodos-pago/      | GET, POST, PUT, DELETE           | Métodos de pago disponibles                  |
| Categoría           | http://127.0.0.1:8000/api/TradConnect/categorias/        | GET, POST, PUT, DELETE           | Clasificación de productos por categoría     |]

# Pruebas
- Apidog
- Postman

## Estructura del proyecto

```plaintext
TradConnect/
├── config/
│   ├── __pycache__/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── TradConnect/
│   ├── __pycache__/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   └── views.py
├── manage.py
└── requirements.txt
```

# Desarrollado por:
Estudiantes de Ingeniería en Sistemas de cuarto semestre de la UNAN-MANAGUA
- Whilton Junior Verrio Carballo
-Junice Abigail Salazar Sanchez
-Katerin Jimena Flores Amador



- Email:
-  [w138jvc@gmail.com]
-  [sanchezjunice61@gmail.com]
-  [fkaterin163@gmail.com]

- GitHub: [Whil138](https://github.com/Whil138)
