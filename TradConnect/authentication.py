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
            if token.get('identity_source') != 'mongo' or type(token.get('auth_version')) is not int:
                raise AuthenticationFailed('Inicia sesion de nuevo con la API actualizada.')
        except Exception as e:
            raise AuthenticationFailed(f'Token inválido: {e}')

        from .identities import resolve
        usuario = resolve(user_id, token.get('company_id'), token.get('auth_version', 0))
        return (usuario, token)

    def authenticate_header(self, request):
        return 'Bearer realm="api"'


class IsUsuarioAutenticado(IsAuthenticated):
    """
    Wrapper explícito de IsAuthenticated.
    Funciona porque Usuario.is_authenticated es una @property que retorna True.
    """
    pass
