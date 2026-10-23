"""Auditoría de claves y vínculos; todas las consultas tienen campos explícitos."""
from collections import defaultdict

from TradConnect import models as sql


ROLE_NAMES = {
    'restaurante': 'Cliente', 'cliente': 'Cliente', 'proveedor': 'Proveedor',
    'admin': 'Administrador', 'administrador': 'Administrador',
}


def compare_keys(expected, actual, limit=20):
    """Los valores son vínculos, nunca documentos completos o credenciales."""
    missing = expected.keys() - actual.keys()
    extra = actual.keys() - expected.keys()
    changed = {key for key in expected.keys() & actual.keys() if expected[key] != actual[key]}

    def summary(keys):
        return {'cantidad': len(keys), 'ids': sorted(keys, key=str)[:limit]}

    return {
        'sql': len(expected), 'mongo': len(actual),
        'faltan_en_mongo': summary(missing), 'sobran_en_mongo': summary(extra),
        'vinculos_distintos': summary(changed),
    }


def expected_user_links(users, companies, roles):
    by_user = defaultdict(list)
    for company_id, user_id, role_id in companies:
        by_user[user_id].append((company_id, role_id))
    links, unsupported = {}, set()
    for user_id, user_role_id in users:
        for company_id, role_id in by_user.get(user_id, [(None, user_role_id)]):
            role = ROLE_NAMES.get(roles.get(role_id, '').casefold())
            if role is None:
                unsupported.add(role_id)
            key = f'uer_sql_{user_id}_{company_id if company_id is not None else "sin_empresa"}'
            links[key] = {'usuario_id': str(user_id),
                          'empresa_id': str(company_id) if company_id is not None else None,
                          'rol_id': role_id, 'nombre_rol': role}
    return links, unsupported


def mongo_rows(database, name, fields):
    # Inclusión explícita: no selecciona correos, nombres, contraseñas o hashes.
    return {doc['_id']: {field: doc.get(field) for field in fields}
            for doc in database[name].find({}, {'_id': 1, **dict.fromkeys(fields, 1)})}


def audit_databases(database, limit=20):
    orders = {pk: {'restauranteid': buyer, 'proveedorid': provider}
              for pk, buyer, provider in sql.Pedido.objects.values_list('pk', 'restauranteid_id', 'proveedorid_id')}
    details = {pk: {'pedidoid': order, 'productoid': product}
               for pk, order, product in sql.Detallepedido.objects.values_list('pk', 'pedidoid_id', 'productoid_id')}
    histories = {pk: {'pedidoid': order, 'estadoid': state}
                 for pk, order, state in sql.Historialestadopedido.objects.values_list('pk', 'pedidoid_id', 'estadoid_id')}
    companies = list(sql.Empresa.objects.values_list('pk', 'usuarioid_id', 'rolid_id'))
    users = list(sql.Usuario.objects.values_list('pk', 'rolid_id'))
    roles = dict(sql.Rol.objects.values_list('pk', 'nombrerol'))
    company_rows = {pk: {'usuarioid': user, 'rolid': role} for pk, user, role in companies}
    role_rows = {pk: {'nombrerol': name} for pk, name in roles.items()}
    report = {}
    for name, expected in (('pedido', orders), ('detallepedido', details),
                           ('historialestadopedido', histories), ('empresa', company_rows), ('rol', role_rows)):
        fields = {'pedido': ('restauranteid', 'proveedorid'),
                  'detallepedido': ('pedidoid', 'productoid'),
                  'historialestadopedido': ('pedidoid', 'estadoid'),
                  'empresa': ('usuarioid', 'rolid'), 'rol': ('nombrerol',)}[name]
        report[name] = compare_keys(expected, mongo_rows(database, name, fields), limit)

    # Compara los IDs anidados además del vínculo comprador/proveedor.
    grouped_details, grouped_history = defaultdict(set), defaultdict(set)
    for pk, row in details.items():
        grouped_details[row['pedidoid']].add(pk)
    for pk, row in histories.items():
        grouped_history[row['pedidoid']].add(pk)
    expected_web = {pk: {**row, 'detalles': grouped_details[pk], 'historial': grouped_history[pk]}
                    for pk, row in orders.items()}
    actual_web = {}
    malformed = set()
    projection = {'_id': 1, 'restauranteid': 1, 'proveedorid': 1, 'detalles.id': 1, 'historial.id': 1}
    for doc in database['pedidos_web'].find({}, projection):
        row = {field: doc.get(field) for field in ('restauranteid', 'proveedorid')}
        for field in ('detalles', 'historial'):
            children = doc.get(field)
            if not isinstance(children, list) or any(not isinstance(child, dict) or not isinstance(child.get('id'), int) for child in children):
                malformed.add(doc['_id'])
                row[field] = None
            else:
                row[field] = {child['id'] for child in children}
                if len(row[field]) != len(children):
                    malformed.add(doc['_id'])
        actual_web[doc['_id']] = row
    report['pedidos_web'] = compare_keys(expected_web, actual_web, limit)
    report['pedidos_web']['estructura_invalida'] = {'cantidad': len(malformed), 'ids': sorted(malformed, key=str)[:limit]}

    expected_links, unsupported = expected_user_links(users, companies, roles)
    fields = ('usuario_id', 'empresa_id', 'rol_id', 'nombre_rol')
    actual_links = mongo_rows(database, 'usuarios_empresas_roles', fields)
    report['usuarios_empresas_roles'] = compare_keys(expected_links, actual_links, limit)
    report['usuarios_empresas_roles']['roles_sql_sin_equivalencia'] = {
        'cantidad': len(unsupported), 'ids': sorted(unsupported)[:limit]}
    for label, expected, field in (
        ('usuarios', {str(pk) for pk, _ in users}, 'usuario_id'),
        ('empresas', {str(pk) for pk, _, _ in companies}, 'empresa_id'),
    ):
        actual = {row[field] for row in actual_links.values() if row[field] is not None}
        report[f'{label}_en_vinculos'] = compare_keys(dict.fromkeys(expected), dict.fromkeys(actual), limit)
    return report


def has_differences(report):
    return any(section[key]['cantidad'] for section in report.values()
               for key in ('faltan_en_mongo', 'sobran_en_mongo', 'vinculos_distintos',
                           'estructura_invalida', 'roles_sql_sin_equivalencia')
               if key in section)
