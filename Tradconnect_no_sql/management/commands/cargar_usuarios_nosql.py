from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from pymongo import ReplaceOne
from pymongo.errors import PyMongoError
from rest_framework.exceptions import ValidationError

from config.mongodb import get_database
from TradConnect.models import Empresa, Usuario
from Tradconnect_no_sql.services import validate_document


class Command(BaseCommand):
    help = 'Carga usuarios, empresas y roles SQL como documentos; conserva la autenticación SQL.'

    def add_arguments(self, parser):
        parser.add_argument('--validar', action='store_true')

    def handle(self, *args, **options):
        roles = {'restaurante': ('Cliente', 'Restaurante'),
                 'cliente': ('Cliente', 'Restaurante'),
                 'proveedor': ('Proveedor', 'Proveedor'),
                 'admin': ('Administrador', 'Interna'),
                 'administrador': ('Administrador', 'Interna')}
        count = 0
        try:
            collection = get_database()['usuarios_empresas_roles']
            # Cada usuario puede tener varias empresas; se conserva un vínculo por empresa.
            for user in Usuario.objects.select_related('rolid').order_by('pk').iterator():
                companies = list(Empresa.objects.filter(usuarioid=user).select_related('rolid'))
                for company in companies or [None]:
                    role = company.rolid if company else user.rolid
                    mapped = roles.get(role.nombrerol.casefold())
                    if mapped is None:
                        raise CommandError(f'Rol SQL {role.pk} sin equivalencia NoSQL; revisa el catálogo.')
                    document = validate_document('usuarios_empresas_roles', {
                        'empresa_id': str(company.pk) if company else None,
                        'razon_social': company.razonsocial if company else None,
                        'ruc': company.ruc if company else None,
                        'tipo_empresa': mapped[1],
                        'telefono_empresa': company.telefono if company else None,
                        'direccion_fiscal': company.direccionfiscal if company else None,
                        'usuario_id': str(user.pk), 'nombre_usuario': user.nombreusuario,
                        'correo': user.correoelectronico, 'password_hash': user.contrasena,
                        # SQL no tiene estado de usuario ni fecha de asignación separados.
                        'estado_usuario': True, 'rol_id': role.pk, 'nombre_rol': mapped[0],
                        'estado_rol': company.estado is not False if company else True,
                        'fecha_asignacion': user.fecharegistro,
                        'fecha_registro': user.fecharegistro,
                    })
                    document['_id'] = f'uer_sql_{user.pk}_{company.pk if company else "sin_empresa"}'
                    if not options['validar']:
                        collection.bulk_write([ReplaceOne({'_id': document['_id']}, document, upsert=True)])
                    count += 1
            self.stdout.write(self.style.SUCCESS(f'{count} vínculos ' + ('validados.' if options['validar'] else 'cargados.')))
        except ValidationError as exc:
            raise CommandError(f'Usuario SQL {user.pk}: {exc.detail}') from exc
        except (ImproperlyConfigured, DatabaseError, PyMongoError) as exc:
            raise CommandError('Carga incompleta; revisa las conexiones. Puedes repetirla sin duplicar vínculos.') from exc
