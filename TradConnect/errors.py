import logging

from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.db import DatabaseError, IntegrityError
from pymongo.errors import PyMongoError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    if isinstance(exc, ObjectDoesNotExist):
        return Response({
            'error': 'El recurso solicitado no existe.',
            'code': 'not_found',
        }, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, IntegrityError):
        logger.exception('La base de datos rechazó una operación por integridad.')
        return Response({
            'error': 'La operación no cumple las restricciones de la base de datos.',
            'code': 'database_conflict',
        }, status=status.HTTP_409_CONFLICT)

    if isinstance(exc, (PyMongoError, DatabaseError, ImproperlyConfigured)):
        view = context.get('view')
        logger.exception(
            'Error de base de datos en el endpoint %s.',
            view.__class__.__name__ if view else 'desconocido',
        )
        return Response({'detail': 'La base de datos no esta disponible o su esquema no coincide. Revisa la configuracion del servidor.'}, status=503)
    return exception_handler(exc, context)
