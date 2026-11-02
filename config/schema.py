"""Documentación conjunta sin cambiar rutas, permisos ni métodos de la API."""
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema


SQL_RESOURCES = {
    'auth': 'Autenticación', 'empresas': 'Empresas', 'sucursales': 'Sucursales',
    'productos': 'Productos', 'pedidos': 'Pedidos', 'inventario': 'Inventario',
    'promociones': 'Promociones', 'detalles-pedido': 'Detalles de pedido',
    'historial-estado': 'Historial de estados', 'documentos-sucursal': 'Documentos de sucursal',
    'dashboard': 'Dashboard', 'marketplace': 'Marketplace', 'categorias': 'Categorías',
    'unidades-medida': 'Unidades de medida', 'monedas': 'Monedas',
    'metodos-pago': 'Métodos de pago', 'estados-pedido': 'Estados de pedido',
    'departamentos': 'Departamentos', 'municipios': 'Municipios',
    'tipos-documento': 'Tipos de documento',
}


class HybridAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys=None):
        parts = self.path.strip('/').split('/')
        if parts and parts[0] == 'api':
            parts = parts[1:]
        if parts and parts[0] == 'nosql':
            resource = parts[1] if len(parts) > 1 else 'Colecciones'
            if resource.startswith('{'):
                resource = 'Proyecciones SQL'
            return [f'MongoDB / {resource}']
        resource = parts[0] if parts else 'API'
        return [f'SQL Server / {SQL_RESOURCES.get(resource, resource)}']


class HybridSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request=request, public=public)
        if schema is not None:
            tags = {tag for item in schema.paths.values() for method, operation in item.items()
                    if method in ('get', 'post', 'put', 'patch', 'delete')
                    for tag in operation.get('tags', [])}
            # SQL primero, después Mongo, con todos los métodos de cada recurso juntos.
            schema.tags = [{'name': tag} for tag in sorted(tags, key=lambda tag: (not tag.startswith('SQL Server /'), tag))]
        return schema
