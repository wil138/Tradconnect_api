"""
URL configuration for tradconnect_api project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .schema import HybridSchemaGenerator
from .connections import ConfigurationView, ConnectionsView, ConnectionsPage

schema_view = get_schema_view(
    openapi.Info(
        title="TradConnect API - SQL Server + MongoDB",
        default_version='v1',
        description="Documentación interactiva de la API de TradConnect - Plataforma B2B para Restaurantes y Proveedores",
        terms_of_service="https://www.tradconnect.com/terms/",
        contact=openapi.Contact(email="soporte@tradconnect.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    generator_class=HybridSchemaGenerator,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='schema-swagger-ui', permanent=False), name='api-home'),
    path('admin/', admin.site.urls),
    path('conexiones/', ConnectionsPage.as_view(), name='connections-page'),
    path('api/configuracion/', ConfigurationView.as_view(), name='api-configuration'),
    path('api/conexiones/', ConnectionsView.as_view(), name='api-connections'),

    # API principal (rutas de la app TradConnect, por ejemplo usuarios, productos, etc.)
    path('api/', include('TradConnect.urls')),

    # API MongoDB, publicada junto a la API SQL en el mismo esquema Swagger.

    path('api/nosql/', include('Tradconnect_no_sql.urls')),

    # Documentación Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger.yaml/', schema_view.without_ui(cache_timeout=0), name='schema-yaml'),
]
