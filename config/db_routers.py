class DWAnalyticsRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'WD_TradConnect':
            return 'trad_dw'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'WD_TradConnect':
            return 'trad_dw'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.app_label == 'WD_TradConnect' or obj2._meta.app_label == 'WD_TradConnect':
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'WD_TradConnect':
            return db == 'trad_dw'
        return db == 'default'