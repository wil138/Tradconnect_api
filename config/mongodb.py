from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from functools import lru_cache

@lru_cache(maxsize=1)
def get_client():
    from pymongo import MongoClient
    if not settings.MONGODB_URI:
        raise ImproperlyConfigured('Define MONGODB_URI para usar MongoDB.')
    return MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)

def get_database():
    return get_client()[settings.MONGODB_DATABASE]


def __getattr__(name):
    if name == 'database':
        return get_database()
    if name == 'client':
        return get_client()
    raise AttributeError(name)
