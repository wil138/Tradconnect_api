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
        return get_database()[self.sql_model._meta.model_name.removeprefix('sql')]

    def serialize(self, instance):
        return {'_id': instance.pk, **{
            field.name: document_value(getattr(instance, field.attname))
            for field in self.sql_model._meta.concrete_fields
        }}


def get_document_models():
    from TradConnect import sql_models
    from django.db.models import Model
    return {model._meta.model_name.removeprefix('sql'): DocumentModel(model)
            for model in vars(sql_models).values()
            if isinstance(model,type) and issubclass(model,Model) and model is not Model}
