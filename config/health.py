import logging

from django.apps import apps
from django.db import DatabaseError, connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
def api_configuration(request):
    return JsonResponse({
        'api_base_url': request.build_absolute_uri('/api').rstrip('/'),
    })


@require_GET
def connection_status(request):
    try:
        connection = connections['default']
        connection.ensure_connection()
        existing_tables = set(connection.introspection.table_names())
    except DatabaseError:
        logger.exception('No se pudo verificar la conexión con la base de datos.')
        return JsonResponse({
            'api': 'available',
            'database': 'unavailable',
            'error': 'No se pudo conectar a la base de datos.',
        }, status=503)

    required_tables = {
        model._meta.db_table
        for model in apps.get_app_config('TradConnect').get_models()
    }
    missing_tables = sorted(required_tables - existing_tables)
    if missing_tables:
        return JsonResponse({
            'api': 'available',
            'database': 'connected',
            'schema': 'incomplete',
            'missing_tables': missing_tables,
            'error': 'Faltan tablas requeridas por la API.',
        }, status=503)

    return JsonResponse({
        'api': 'available',
        'database': 'connected',
        'schema': 'ready',
    })
