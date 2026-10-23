"""Configuracion publica y comprobaciones de lectura, registradas en urls.py central."""
from django.db import connection
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from config.mongodb import get_database


def public_links(request):
    url=lambda name:request.build_absolute_uri(reverse(name))
    return {'api_base_url':url('api-root').rstrip('/'), 'api_root_url':url('api-root'),
        'configuration_url':url('api-configuration'), 'connections_url':url('api-connections'),
        'connections_page_url':url('connections-page'), 'swagger_url':url('schema-swagger-ui'),
        'redoc_url':url('schema-redoc'), 'schema_url':url('schema-json'),
        'marketplace_url':url('marketplace-list'), 'login_url':url('auth-login'),
        'nosql_orders_url':url('nosql-my-orders')}


def check_sql():
    # Conexion independiente con timeout; no altera la conexion usada por la API.
    probe=None
    try:
        probe=connection.copy(alias='connection_probe')
        probe.settings_dict['OPTIONS']={**probe.settings_dict.get('OPTIONS',{}),'connection_timeout':3,'query_timeout':3}
        with probe.cursor() as cursor:
            cursor.execute('SELECT 1'); cursor.fetchone()
            cursor.execute("SELECT COUNT(DISTINCT TABLE_NAME) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' AND TABLE_NAME IN ('Producto','Pedido','Sucursal')")
            ready=cursor.fetchone()[0]==3
        return {'connected':True,'ready':ready,'message':'Conexion y tablas principales disponibles.' if ready else 'Conexion disponible; revisa las tablas Producto, Pedido y Sucursal.'}
    except Exception:
        return {'connected':False,'ready':False,'message':'No se pudo conectar. Revisa SQLSERVER_HOST, autenticacion, driver y permisos.'}
    finally:
        if probe is not None:
            probe.close()


def check_mongo():
    if not settings.MONGODB_URI:
        return {'connected':False,'ready':False,'message':'Falta MONGODB_URI en el entorno del servidor.'}
    try:
        db=get_database(); db.command('ping')
        ready=bool(db.list_collection_names(filter={'name':'usuarios_empresas_roles'}))
        return {'connected':True,'ready':ready,'message':'Conexion e identidades disponibles.' if ready else 'Conexion disponible; revisa MONGODB_DATABASE y la coleccion usuarios_empresas_roles.'}
    except Exception:
        return {'connected':False,'ready':False,'message':'No se pudo conectar. Revisa MONGODB_URI, la base seleccionada y los permisos.'}


class ConfigurationView(APIView):
    authentication_classes=[]
    permission_classes=[AllowAny]
    def get(self,request):
        return Response(public_links(request),headers={'Cache-Control':'no-store'})


class ConnectionsView(APIView):
    authentication_classes=[]
    permission_classes=[AllowAny]
    def get(self,request):
        databases={'sql':check_sql(),'mongodb':check_mongo()}
        ready=all(value['ready'] for value in databases.values())
        return Response({'status':'ok' if ready else 'degraded','checked_at':timezone.now().isoformat(),
            'databases':databases,'links':public_links(request)}, status=200 if ready else 503,
            headers={'Cache-Control':'no-store'})


class ConnectionsPage(TemplateView):
    template_name='config/connections.html'
