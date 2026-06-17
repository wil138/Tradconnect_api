# TradConnect/authentication.py
# Backends de autenticación propios para el modelo Usuario personalizado.
# Separado de views.py para evitar importación circular con DRF settings.

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import AccessToken


class UsuarioJWTAuthentication(BaseAuthentication):
    """
    Backend JWT que resuelve el modelo Usuario propio.
    simplejwt nativo llama a get_user_model() y obtiene auth.User,
    no el Usuario personalizado de TradConnect (que no hereda de AbstractBaseUser).
    Este backend extrae user_id del token y devuelve el Usuario correcto.
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None  # No es JWT — dejar pasar a otros backends

        token_str = auth_header.split(' ', 1)[1]
        try:
            token = AccessToken(token_str)
            user_id = token['user_id']
        except Exception as e:
            raise AuthenticationFailed(f'Token inválido: {e}')

        # Importación local para evitar circular import al arrancar Django
        from TradConnect.models import Usuario
        try:
            usuario = Usuario.objects.get(id=user_id)
        except Usuario.DoesNotExist:
            raise AuthenticationFailed('Usuario no encontrado')

        return (usuario, token)

    def authenticate_header(self, request):
        return 'Bearer realm="api"'


class IsUsuarioAutenticado(IsAuthenticated):
    """
    Wrapper explícito de IsAuthenticated.
    Funciona porque Usuario.is_authenticated es una @property que retorna True.
    """
    pass
