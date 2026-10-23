from django.db import DatabaseError
from django.core.exceptions import ImproperlyConfigured
from pymongo.errors import PyMongoError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, (PyMongoError, DatabaseError, ImproperlyConfigured)):
        return Response({'detail': 'La base de datos no esta disponible o su esquema no coincide. Revisa la configuracion del servidor.'}, status=503)
    return exception_handler(exc, context)
