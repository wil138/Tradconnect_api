from django.apps import AppConfig


class TradconnectNoSqlConfig(AppConfig):
    name = 'Tradconnect_no_sql'

    def ready(self):
        from . import signals  # noqa: F401
