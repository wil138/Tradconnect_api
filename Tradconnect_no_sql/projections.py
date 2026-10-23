"""Proyecciones MongoDB de los modelos SQL. SQL conserva la escritura y los IDs."""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from django.apps import apps
from config.mongodb import get_database


def document_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


@dataclass(frozen=True)
class DocumentModel:
    sql_model: type

    @property
    def collection(self):
        return get_database()[self.sql_model._meta.model_name]

    def serialize(self, instance):
        return {'_id': instance.pk, **{
            field.name: document_value(getattr(instance, field.attname))
            for field in self.sql_model._meta.concrete_fields
        }}


def get_document_models():
    # No copiar contraseñas ni hashes a la base documental.
    return {model._meta.model_name: DocumentModel(model)
            for model in apps.get_app_config('TradConnect').get_models()
            if model._meta.model_name != 'usuario'}
