"""Identidad MongoDB compartida por JWT, permisos y datos de empresa."""
import re
from types import SimpleNamespace
from django.contrib.auth.hashers import check_password
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, NotFound
from config.mongodb import get_database


def users():
    return get_database()['usuarios_empresas_roles']


def exact(value):
    return {'$regex': '^' + re.escape(str(value)) + '$', '$options': 'i'}


class Principal:
    is_authenticated = True
    is_anonymous = False
    def __init__(self, document):
        self.document = document
        user_id = document.get('usuario_id')
        role_name = document.get('nombre_rol')
        if not isinstance(user_id, (str, int)) or not str(user_id).strip():
            raise AuthenticationFailed('La cuenta no tiene un identificador válido. Contacta soporte.')
        if not isinstance(role_name, str) or not role_name.strip():
            raise AuthenticationFailed('La cuenta no tiene un rol válido. Contacta soporte.')
        self.pk = self.id = str(user_id)
        self.company_id = document.get('empresa_id')
        self.rolid = SimpleNamespace(nombrerol=role_name.strip())
        self.is_active = document.get('estado_usuario') is True and document.get('estado_rol') is True
        self.version = document.get('auth_version', 0)

    @property
    def role(self):
        value = self.rolid.nombrerol.casefold()
        return 'provider' if value == 'proveedor' else 'client' if value in ('cliente', 'restaurante') else 'admin' if value in ('admin', 'administrador') else 'staff'


def resolve(user_id, company_id=None, version=None):
    query = {'usuario_id': str(user_id), 'estado_usuario': True, 'estado_rol': True}
    if company_id is not None:
        query['empresa_id'] = company_id
    doc = users().find_one(query, sort=[('_id', 1)])
    if not doc or (version is not None and doc.get('auth_version', 0) != version):
        raise AuthenticationFailed('Sesion invalida, inactiva o revocada.')
    return Principal(doc)


def authenticate_credentials(username, password):
    docs = list(users().find({'$or': [{'correo': exact(username)}, {'nombre_usuario': exact(username)}]}).sort('_id', 1))
    if not docs or len({str(doc.get('usuario_id')) for doc in docs}) != 1:
        raise AuthenticationFailed('Usuario o contrasena incorrectos.')
    doc = next((item for item in docs if item.get('estado_usuario') is True and item.get('estado_rol') is True), docs[0])
    password_hash = doc.get('password_hash')
    try:
        password_matches = isinstance(password_hash, str) and bool(password_hash) and check_password(password, password_hash)
    except ValueError:
        password_matches = False
    if not password_matches:
        raise AuthenticationFailed('Usuario o contrasena incorrectos.')
    principal = Principal(doc)
    if not principal.is_active:
        raise PermissionDenied('Cuenta inactiva. Solicita su activacion.')
    return principal


def company(request, provider=None):
    principal = request.user
    if not isinstance(principal, Principal):
        raise PermissionDenied('Se requiere una identidad MongoDB.')
    if provider is not None and principal.role != ('provider' if provider else 'client'):
        raise PermissionDenied('El rol no permite esta operacion.')
    if not principal.company_id:
        raise PermissionDenied('El usuario no tiene empresa asignada.')
    return SimpleNamespace(pk=principal.company_id, id=principal.company_id,
        razonsocial=principal.document.get('razon_social', ''), ruc=principal.document.get('ruc', ''))


def company_names(ids):
    names = {}
    for doc in users().find({'empresa_id': {'$in': list(ids)}}, {'empresa_id':1, 'razon_social':1}):
        company_id = doc.get('empresa_id')
        name = doc.get('razon_social')
        if company_id is not None and isinstance(name, str) and name.strip():
            names[company_id] = name.strip()
    return names


def user_data(principal):
    doc=principal.document
    email=doc.get('correo')
    email=email.strip() if isinstance(email,str) else ''
    name=doc.get('nombre_usuario')
    name=name.strip() if isinstance(name,str) else ''
    return {'id':principal.pk, 'rolid':doc.get('rol_id'), 'rol_nombre':doc['nombre_rol'],
        'nombreusuario':name or email, 'correoelectronico':email,
        'fecharegistro':doc.get('fecha_registro'), 'telefono':doc.get('telefono_usuario') or doc.get('telefono_empresa') or ''}


def company_data(principal):
    doc=principal.document
    if not doc.get('empresa_id'):
        return None
    return {'id':doc['empresa_id'], 'usuarioid':principal.pk, 'rolid':doc.get('rol_id'),
        'razonsocial':doc.get('razon_social') or '', 'ruc':doc.get('ruc') or '', 'telefono':doc.get('telefono_empresa') or '',
        'correoempresa':doc.get('correo_empresa') or '', 'direccionfiscal':doc.get('direccion_fiscal') or '',
        'logourl':doc.get('logo_url') or '', 'estado':doc.get('estado_rol',False)}
