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
