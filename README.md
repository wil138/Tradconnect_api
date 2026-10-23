# TradConnect API

> **Servidor Django de este proyecto:** `python manage.py runserver 127.0.0.1:8001`.
> Swagger: http://localhost:8001/swagger/ · Conexiones: http://localhost:8001/conexiones/.
> Se mantiene `config/urls.py` como entrada central. La configuración privada local
> se carga automáticamente; las variables de entorno tienen prioridad.


Documentación de la API activa en `TradConnect_Api`. El servicio usa Django REST
Framework y combina identidades/sesiones documentales en MongoDB con los datos
transaccionales y catálogos existentes en SQL Server.

## Documentación interactiva

Con el servidor iniciado:

- `http://127.0.0.1:8000/` redirige a Swagger.
- `http://127.0.0.1:8000/swagger/` muestra Swagger UI.
- `http://127.0.0.1:8000/redoc/` muestra ReDoc.
- `http://127.0.0.1:8000/swagger.json/` y `/swagger.yaml/` exponen el esquema OpenAPI.

Las rutas de negocio SQL comienzan con `/api/`; las rutas documentales y de
analítica comienzan con `/api/nosql/`.

## Arquitectura y datos

- **MongoDB** almacena las identidades de inicio de sesión y las 13 colecciones
  documentales. El registro web crea el usuario/empresa en
  `usuarios_empresas_roles`.
- **SQL Server** contiene los catálogos y las entidades de negocio operativas
  (productos, sucursales, inventario, pedidos, etc.). Se accede a las tablas
  existentes mediante `TradConnect/sql_models.py`; esos modelos no crean ni
  migran las tablas de negocio.
- El JWT identifica al usuario MongoDB y lleva el ámbito de empresa y la versión
  de autenticación. La API comprueba el rol y limita los recursos SQL a la
  empresa correspondiente.
- No hay transacción distribuida entre MongoDB y SQL Server. La cotización de
  pedidos y las escrituras de colecciones tienen validaciones propias, pero no
  equivalen a una transacción común entre las dos bases.

## Instalación y configuración

Desde la carpeta `TradConnect_Api`:

```powershell
python -m pip install -r requirements.txt

# Ajusta los valores al servidor SQL Server local.
$env:SQLSERVER_HOST = 'SERVIDOR\INSTANCIA'
$env:SQLSERVER_DATABASE = 'TradConnect'
# Opcional: autenticación SQL en vez de la cuenta Windows del proceso.
$env:SQLSERVER_USER = 'usuario'
$env:SQLSERVER_PASSWORD = 'contraseña'

# MongoDB es necesario para autenticación, colecciones y analítica de feedback.
$env:MONGODB_URI = 'mongodb://localhost:27017'
$env:MONGODB_DATABASE = 'tradconnect'

python manage.py check
python manage.py runserver
```

`SQLSERVER_HOST` y `SQLSERVER_DATABASE` también tienen valores por defecto en
`config/settings.py`; configura explícitamente los valores del entorno. Si no se
define `SQLSERVER_USER`, el backend intenta usar la cuenta Windows del proceso.
El driver ODBC predeterminado es `ODBC Driver 17 for SQL Server`; se puede cambiar
con `SQLSERVER_DRIVER`. `SQLSERVER_PORT` es opcional.

`MONGODB_URI` no tiene valor predeterminado: debe configurarse para usar MongoDB.
La moneda configurada para el marketplace se fija mediante
`MARKETPLACE_CURRENCY_ID` (por defecto `1`). No guardes credenciales en archivos
versionados ni en ejemplos que vayas a publicar.

Las migraciones de Django solo administran tablas internas de Django. No crean
ni reparan las tablas de negocio SQL marcadas como `managed=False`. Comprueba la
conexión y el esquema existente antes de ejecutar importaciones o probar CRUD.

## Convenciones HTTP

- Los cuerpos y respuestas de escritura usan JSON.
- Las rutas protegidas requieren `Authorization: Bearer <access>`.
- El token de acceso dura 60 minutos y el refresh token un día, según la
  configuración actual de SimpleJWT.
- Las colecciones documentales paginadas responden
  `{"limit": n, "offset": n, "results": [...]}`. `limit` admite de 1 a 500;
  `offset` debe ser un entero no negativo.
- Los serializadores SQL y los modelos Pydantic publicados en Swagger son la
  referencia final para los campos y tipos del esquema instalado.

Ejemplo de inicio de sesión:

```http
POST /api/auth/login/
Content-Type: application/json

{"username":"correo@ejemplo.com","password":"contraseña"}
```

La respuesta incluye `tokens.access`, `tokens.refresh`, `usuario`, `empresa`,
`catalogos`, `sucursales`, `productos`, `inventario`, `promociones`,
`pedidos_comprador`, `pedidos_proveedor`, `moneda_catalogo_id` y `estadisticas`.

## API SQL

Salvo marketplace y catálogos, las rutas requieren JWT. Los listados SQL no
declaran paginación propia; el alcance depende del recurso y del rol.

### Autenticación y perfil

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/auth/register/` | Público | Registra identidad y empresa en MongoDB. |
| `POST` | `/api/auth/login/` | Público | Inicia sesión y devuelve tokens más el snapshot de la empresa. |
| `POST` | `/api/auth/refresh/` | Público | Recibe `{"refresh":"..."}` y devuelve un nuevo `access`. |
| `GET` | `/api/auth/me/` | JWT | Devuelve la identidad autenticada. |
| `GET` | `/api/auth/my-data/` | JWT | Devuelve el snapshot actualizado de la empresa; conserva el token existente. |
| `POST` | `/api/auth/dump-all/` | Credenciales | Alias de compatibilidad de `login`; acepta el mismo cuerpo y respuesta. |
| `PUT` | `/api/auth/update-profile/` | JWT | Actualiza `nombreusuario`, `correoelectronico` y/o `telefono`. |
| `POST` | `/api/auth/change-password/` | JWT | Recibe `old_password` y `new_password`; rota la versión de autenticación y devuelve tokens. |

Registro: `nombre_usuario`, `correo`, `contrasena` (8–128 caracteres), `rol`
(`restaurant` o `provider`), `razon_social`, `ruc` y `telefono` son obligatorios.
`direccion_fiscal` y `logo_url` son opcionales. La respuesta de registro es
`{"usuario": ...}`; después hay que iniciar sesión para obtener tokens.

La actualización de perfil solo acepta los tres campos indicados y rechaza
campos adicionales. El cambio de contraseña valida la contraseña actual y aplica
los validadores de Django.

### Recursos SQL

`CRUD` indica listado/detalle y las operaciones de escritura disponibles. Para
los cuerpos completos, consulta el esquema OpenAPI, ya que varios serializadores
se generan directamente desde el modelo SQL instalado.

| Recurso | Rutas | Métodos | Acceso y alcance |
|---|---|---|---|
| Empresas | `/api/empresas/`, `/api/empresas/{id}/`, `/api/empresas/{id}/sucursales/` | `GET`; `PATCH` y `PUT` en detalle; sucursales `GET` | Solo la empresa del usuario. No hay alta/baja de empresa en este recurso. |
| Sucursales | `/api/sucursales/`, `/api/sucursales/{id}/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | JWT; se asigna la empresa desde el JWT. `DELETE` marca la sucursal inactiva. |
| Productos | `/api/productos/`, `/api/productos/{id}/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | Proveedores; limitado a sus productos. `DELETE` marca el producto eliminado. |
| Marketplace | `/api/marketplace/`, `/api/marketplace/{id}/` | `GET` | Público; solo productos activos con stock en sucursales activas. |
| Inventario | `/api/inventario/`, `/api/inventario/{id}/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | Proveedores; producto y sucursal deben pertenecer a su empresa. |
| Promociones | `/api/promociones/`, `/api/promociones/{id}/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | Proveedores; el producto debe ser propio y el descuento estar entre 0 y 100. |
| Pedidos | `/api/pedidos/`, `/api/pedidos/{id}/` | `GET`, `POST` | Compradores y proveedores relacionados al pedido. |
| Cotización | `/api/pedidos/cotizar/` | `POST` | Compradores; valida precio, promociones, moneda, sucursales y stock. |
| Estado de pedido | `/api/pedidos/{id}/update_status/` | `PUT` | Proveedor propietario del pedido; recibe `estado_id` y, opcionalmente, `comentario`. |
| Detalles de pedido | `/api/detalles-pedido/`, `/api/detalles-pedido/{id}/` | `GET` | Solo pedidos relacionados con la empresa autenticada. |
| Documentos de sucursal | `/api/documentos-sucursal/`, `/api/documentos-sucursal/{id}/` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE` | JWT; la sucursal debe pertenecer a la empresa. |
| Dashboard | `/api/dashboard/summary/`, `/api/dashboard/sales_chart/`, `/api/dashboard/recent_orders/` | `GET` | Proveedores; estadísticas, series de venta y hasta cinco pedidos recientes. |

El marketplace acepta los filtros opcionales `categoria`, `proveedor` y
`search`, por ejemplo:

```text
GET /api/marketplace/?categoria=2&proveedor=10&search=arroz
```

El serializador de producto expone datos del producto, `categoria_nombre`,
`unidad_nombre`, `inventario`, `promociones`, `precio_original`, `precio_final`,
`descuento`, `promocion_activa` y `sucursal_origen_id`. Para crear un producto se
envían los campos SQL editables (`nombreproducto`, `descripcion`, `precioventa`,
`categoriaid`, `unidadmedidaid`, etc.). `cantidadminimapedido` tiene valor por
defecto `1`. Al crear, `stock_inicial` junto con `sucursal_id` registra stock
inicial en una sucursal activa propia. Al actualizar, `stock_disponible` junto
con `sucursal_id` ajusta el stock de esa sucursal.

Inventario acepta los campos del modelo, incluidos `productoid`, `sucursalid`,
`stockdisponible` y `stockminimo`; el stock no puede ser negativo y solo puede
haber un registro por producto y sucursal.

### Cotizar y crear pedidos

Cotizar y crear usan el mismo cuerpo. La compra debe confirmarse con el
`quote_token` devuelto por la cotización:

```json
{
  "proveedor_id": "ID_EMPRESA",
  "sucursal_origen_id": 4,
  "sucursal_entrega_id": 8,
  "metodo_pago_id": 2,
  "moneda_id": 1,
  "items": [
    {"producto_id": 17, "cantidad": 2.5}
  ],
  "comentario": "Entrega en horario de mañana"
}
```

`GET` no aplica: primero usa `POST /api/pedidos/cotizar/`. La respuesta de
cotización contiene `subtotal`, `ahorro`, `impuesto`, `totalneto`, `moneda_id`,
`detalles` y `quote_token`. Después envía el mismo cuerpo más
`quote_token` a `POST /api/pedidos/`. El token firmado vence a los cinco minutos;
si cambian el precio, la promoción o el stock, hay que volver a cotizar.
Se aceptan de 1 a 100 productos, cantidades positivas con hasta dos decimales,
una moneda igual a `MARKETPLACE_CURRENCY_ID`, sucursales activas correctas y
stock suficiente. Los precios y descuentos se calculan en el servidor; no se
aceptan precios aportados por el cliente.

### Catálogos públicos de solo lectura

| Ruta | Recurso |
|---|---|
| `/api/categorias/` | Categorías |
| `/api/unidades-medida/` | Unidades de medida |
| `/api/monedas/` | Monedas |
| `/api/metodos-pago/` | Métodos de pago |
| `/api/estados-pedido/` | Estados de pedido |
| `/api/departamentos/` | Departamentos |
| `/api/municipios/` | Municipios |
| `/api/tipos-documento/` | Tipos de documento |

Cada ruta admite `GET` de colección y `GET /{id}/`. No admite escrituras.

## API MongoDB

### Colecciones documentales: administración

`GET /api/nosql/esquemas/` devuelve los esquemas JSON de las 13 colecciones:

1. `usuarios_empresas_roles`
2. `preferencias_negocio`
3. `preferencias_categorias`
4. `preferencias_productos`
5. `preferencias_metodos_pago`
6. `evaluaciones_proveedores`
7. `transacciones_no_exitosas`
8. `sustituciones_ofrecidas`
9. `incidencias_entregas`
10. `evidencias_incidencia`
11. `comentarios_post_compra`
12. `interacciones_comentario`
13. `necesidades_no_satisfechas`

Cada colección admite `GET` y `POST` en
`/api/nosql/{coleccion}/`; cada documento admite `GET`, `PUT`, `PATCH` y
`DELETE` en `/api/nosql/{coleccion}/{id}/`. Estas operaciones administrativas
requieren JWT de rol `Admin` o `Administrador`.

- `GET` de colección acepta `limit` y `offset`; responde
  `{"limit": ..., "offset": ..., "results": [...]}`.
- `POST` valida el documento completo y genera `_id`; responde `201`.
- `PUT` reemplaza el documento completo.
- `PATCH` combina los cambios con el documento y valida el resultado completo.
- `DELETE` responde `204`; no permite eliminar documentos que tengan referencias
  documentales conocidas.
- Las referencias SQL (`*_id_sql`) se validan contra SQL Server. Las referencias
  entre documentos se validan en MongoDB.
- `password_hash` nunca se devuelve. Al escribir en
  `usuarios_empresas_roles`, debe ser un hash reconocido por Django; no se
  aceptan contraseñas en texto plano.

Campos principales de los esquemas:

| Colección | Campos requeridos o relevantes |
|---|---|
| `usuarios_empresas_roles` | `tipo_empresa`, `usuario_id`, `nombre_usuario`, `correo`, `password_hash`, `estado_usuario`, `rol_id`, `nombre_rol`, `estado_rol`, `fecha_asignacion`, `fecha_registro`; datos de empresa/sucursal son opcionales según rol y validador. |
| `preferencias_negocio` | `empresa_id`, `usuario_id`, `horario_entrega_preferido`, `fecha_actualizacion`. |
| `preferencias_categorias` | `preferencia_id`, `categoria_id_sql`. |
| `preferencias_productos` | `preferencia_id`, `producto_id_sql`, `nombre`. |
| `preferencias_metodos_pago` | `preferencia_id`, `metodo_pago_id_sql`. |
| `evaluaciones_proveedores` | pedido, cliente y proveedor; `puntuacion`, `calidad`, `tiempo_entrega`, `precio`, `atencion` (1–5) y `fecha`; comentario opcional. |
| `transacciones_no_exitosas` | fecha de intento, cliente, proveedor, motivo y monto tentativo; pedido opcional. |
| `sustituciones_ofrecidas` | `transaccion_id`, `producto_solicitado`, `producto_alternativo_ofrecido`. |
| `incidencias_entregas` | pedido, cliente, proveedor, `tipo_incidencia`, `tipo_reclamo`, estado y fecha; respuesta del proveedor opcional. |
| `evidencias_incidencia` | `incidencia_id`, `nombre_archivo`, `url`. |
| `comentarios_post_compra` | pedido, cliente, proveedor, `opinion_libre`, `calificacion` (1–5) y fecha. |
| `interacciones_comentario` | `comentario_id`, fecha, tipo, mensaje y `usuario_id`. |
| `necesidades_no_satisfechas` | cliente, `insumo_buscado`, cantidad (>=1), unidad, categoría SQL, estado y fecha. |

Los modelos Pydantic en `Tradconnect_no_sql/models.py` contienen la lista
completa de campos, tipos, enumeraciones y restricciones. Las solicitudes no
admiten claves adicionales. Fechas usan ISO 8601 y los importes decimales se
representan como valores decimales JSON/cadenas según la respuesta serializada.

### Flujos por empresa

Las rutas siguientes derivan la empresa y el rol del JWT; no aceptan que el
cliente determine libremente la identidad propietaria:

| Método | Ruta | Acceso / comportamiento |
|---|---|---|
| `GET` | `/api/nosql/cliente/opciones/` | Restaurante/cliente; devuelve sus pedidos y categorías disponibles para formularios. |
| `GET`, `POST` | `/api/nosql/mi-empresa/{coleccion}/` | Lee y crea registros del cliente en preferencias, evaluaciones, comentarios, incidencias y necesidades. Un proveedor solo puede consultar evaluaciones, comentarios e incidencias. |
| `PATCH` | `/api/nosql/mi-empresa/reclamos/{id}/` | Proveedor propietario; requiere `estado` y `respuesta_proveedor`. |
| `GET` | `/api/nosql/cliente/analitica/` | Analítica de la empresa restaurante autenticada. |
| `GET` | `/api/nosql/proveedor/analitica/` | Analítica de la empresa proveedora autenticada. |
| `GET` | `/api/nosql/mis-pedidos/` | Pedidos sincronizados relacionados con las empresas asociadas al usuario. |
| `GET` | `/api/nosql/mis-pedidos/{id}/` | Consulta un pedido sincronizado dentro del mismo ámbito. |

En `/mi-empresa/{coleccion}/`, las colecciones permitidas son
`preferencias_negocio`, `evaluaciones_proveedores`, `comentarios_post_compra`,
`incidencias_entregas` y `necesidades_no_satisfechas`. La API completa datos de
empresa, usuario, proveedor, pedido, fecha, puntuación promedio o estado según
el flujo; por eso los cuerpos de cliente solo envían los campos editables.
Preferencias de negocio se actualizan por empresa/usuario en vez de duplicarse.
Los listados tienen límite fijo de 50 y aceptan `offset`.

Analítica acepta los parámetros opcionales `start=YYYY-MM-DD`,
`end=YYYY-MM-DD` y `moneda={id}`. El valor predeterminado es desde
`2000-01-01` hasta hoy y la primera moneda configurada. Devuelve monedas,
moneda seleccionada, ventas por mes, estados, cinco productos principales,
categorías, clientes/proveedores y `feedback`. Si MongoDB no está disponible,
el bloque de feedback se devuelve con `{"disponible": false}`; SQL sigue siendo
la fuente de pedidos y ventas.

`/mis-pedidos/` consulta la colección `pedidos_web`, no los pedidos SQL en vivo.
Usa paginación `limit`/`offset` y orden cronológico descendente.

### Proyecciones históricas de solo lectura

Por compatibilidad, `/api/nosql/{nombre_modelo_sql}/` y
`/api/nosql/{nombre_modelo_sql}/{id_entero}/` exponen proyecciones de modelos SQL
en forma documental. Solo admiten `GET`, requieren rol administrador y no
escriben en MongoDB. Las colecciones con esquema documental explícito de la
sección anterior tienen prioridad sobre esta ruta heredada.

## Colecciones y carga de datos

El alta normal de usuario crea `usuarios_empresas_roles`. Los flujos web de
feedback crean preferencias de negocio, evaluaciones, comentarios, incidencias
y necesidades. Las restantes colecciones documentales se alimentan por el
panel administrativo, la API de administración o importación JSON; no se
rellenan automáticamente solo por existir el esquema.

Para importar usuarios desde SQL:

```powershell
python manage.py cargar_usuarios_nosql --validar
python manage.py cargar_usuarios_nosql
```

Para importar colecciones desde un JSON `{ "coleccion": [{ "_id": "...", ... }] }`:

```powershell
python manage.py cargar_documentos_nosql ruta\documentos.json --validar
python manage.py cargar_documentos_nosql ruta\documentos.json
```

El modo `--validar` no escribe. Los documentos de importación requieren `_id`
de texto estable; repetir una carga reemplaza/upserta esos IDs, pero no elimina
documentos ausentes. El lote no es atómico entre colecciones: si falla después
de escribir parte del archivo, corrige el origen y repite la importación.
`cargar_nosql` es un comando histórico para proyecciones, no sustituye la carga
de las 13 colecciones.

## Errores HTTP

| Estado | Significado común |
|---|---|
| `400` | JSON, campos, tipos, reglas de negocio o parámetros inválidos. |
| `401` | Token ausente, inválido, expirado o credenciales incorrectas. |
| `403` | Rol o ámbito de empresa sin permiso para el recurso. |
| `404` | Recurso, documento, colección o relación no encontrada. |
| `503` | Base de datos no disponible, configuración incompleta o esquema incompatible. |

Las respuestas de error DRF suelen usar `detail`; las validaciones de campos
pueden devolver un objeto por campo o una lista de errores. No se debe asumir que
todo error tiene una propiedad `error`.

## Integración con la web

`javascripts/utils/api.js` es el cliente compartido. `api.request()` añade el
JWT, intenta refrescarlo ante un `401` y vuelve a probar la solicitud; los
errores HTTP se devuelven como `{success: false, error}`. Si no hay token, la
función rechaza la promesa antes de enviar la petición. `api.publicRequest()`
permite solicitudes públicas y, si falla una petición con caché habilitada,
puede devolver una copia expirada con `fromCache: true` y `expired: true`; esa
respuesta no confirma que los datos sigan actualizados en el servidor.

`api.analyticsData()` selecciona la ruta de proveedor solo cuando
`localStorage.userRole` es `provider`; para los demás valores usa la analítica
de cliente. Por tanto, admin/staff no debe reutilizar ese helper de analítica de
cliente: esas rutas exigen que el rol de la sesión coincida con el tipo de
empresa.

## Conteo de errores desde el frontend

`javascripts/utils/api.js` conserva contadores en memoria para fallos ocurridos
mediante `api.request()`, `api.publicRequest()` y las solicitudes de refresh:

```js
api.getErrorStats();
// { total, byEndpoint, byStatus, lastErrorAt }

api.resetErrorStats();
```

Las rutas se contabilizan sin query string para no retener búsquedas o filtros;
se guardan cantidades por endpoint y estado (`HTTP_400`, `HTTP_503`,
`CLIENT_AUTH` o `NETWORK_OR_RESPONSE`), no el mensaje ni el cuerpo de error. El
conteo existe únicamente durante la vida de la página y no se envía al servidor.
Las respuestas de catálogo o marketplace servidas desde caché no generan un
fallo mientras no se haga una solicitud fallida a la API.

## Pruebas

Desde `TradConnect_Api`:

```powershell
python manage.py check
python manage.py test Tradconnect_no_sql
```

Las pruebas automatizadas no reemplazan la verificación de conexión con una
instancia SQL Server y MongoDB de desarrollo. Para comprobar el contrato
completo, usa Swagger y realiza pruebas con datos de prueba en ambas bases.


## Servidor central, URL web y panel de conexiones

El proyecto Django publica todo desde `config/urls.py`. Conserva la portada que
redirige a Swagger; el panel no reemplaza la documentación existente.

En este equipo el puerto 8000 está ocupado por otra API (rutas `/sql/` y `/mongo/`).
Esta web está configurada para el Django del proyecto en **8001**:

```powershell
python manage.py runserver 127.0.0.1:8001
```

- Swagger: `http://localhost:8001/swagger/`
- Panel de conexiones: `http://localhost:8001/conexiones/`
- Configuración pública: `http://localhost:8001/api/configuracion/`
- Estado SQL/MongoDB: `http://localhost:8001/api/conexiones/`
- Base de la web: `http://localhost:8001/api`

El panel comprueba SQL con consultas de lectura y MongoDB con ping y la existencia
de `usuarios_empresas_roles`; muestra el estado de ambas bases y enlaces útiles.
Devuelve 503 si una base no está lista y no muestra URI, usuarios ni contraseñas.
La documentación y la configuración pública siguen accesibles si una base falla.

El servidor lee `config/conexiones.local.json` (privado e ignorado por Git).
La plantilla `config/conexiones.example.json` sirve para otras instalaciones.
Admite los valores MONGODB_URI, MONGODB_DATABASE y SQLSERVER_DATABASE/HOST/PORT/
USER/PASSWORD/DRIVER. Las variables de entorno tienen prioridad, por lo que
`configurar-entorno.ps1` sigue funcionando, pero ya no es obligatorio cargarlo
para usar la configuración local de este equipo.

`javascripts/config.js` define la dirección inicial de Django. Al iniciar la web,
`api.loadConfiguration()` consulta la ruta central de configuración y obtiene la
URL base y los enlaces generados con `reverse()`. Solo acepta una configuración
del mismo servidor. Si se cambia el puerto, también debe ajustarse esa dirección
inicial del cliente; las rutas concretas se generan desde Django.
