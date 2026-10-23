from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from .audit import audit_databases, compare_keys, expected_user_links, has_differences


class AuditTests(SimpleTestCase):
    def test_equal_counts_do_not_hide_different_keys(self):
        result = compare_keys({1: None, 2: None}, {1: None, 3: None})
        self.assertEqual(result['faltan_en_mongo']['ids'], [2])
        self.assertEqual(result['sobran_en_mongo']['ids'], [3])
        self.assertTrue(has_differences({'test': result}))

    def test_relationship_mismatch_and_limit_zero(self):
        result = compare_keys({1: {'pedidoid': 7}}, {1: {'pedidoid': 8}}, 0)
        self.assertEqual(result['vinculos_distintos'], {'cantidad': 1, 'ids': []})

    def test_multiple_companies_and_role_translation(self):
        links, unsupported = expected_user_links([(1, 1), (2, 3)],
                                                [(4, 1, 1), (5, 1, 2)],
                                                {1: 'Restaurante', 2: 'Proveedor', 3: 'Admin'})
        self.assertEqual(set(links), {'uer_sql_1_4', 'uer_sql_1_5', 'uer_sql_2_sin_empresa'})
        self.assertEqual(links['uer_sql_1_4']['nombre_rol'], 'Cliente')
        self.assertEqual(links['uer_sql_1_5']['nombre_rol'], 'Proveedor')
        self.assertFalse(unsupported)

    def test_unknown_role_is_reported(self):
        _, unsupported = expected_user_links([(1, 9)], [], {9: 'Otro'})
        self.assertEqual(unsupported, {9})

    def test_audit_only_selects_explicit_fields_and_does_not_write(self):
        database = MagicMock()
        collections = {name: MagicMock() for name in ('pedido', 'detallepedido', 'historialestadopedido',
                       'empresa', 'rol', 'pedidos_web', 'usuarios_empresas_roles')}
        for collection in collections.values():
            collection.find.return_value = []
        database.__getitem__.side_effect = collections.__getitem__
        models = {name: MagicMock() for name in
                  ('Pedido', 'Detallepedido', 'Historialestadopedido', 'Empresa', 'Usuario', 'Rol')}
        with patch.multiple('Tradconnect_no_sql.audit.sql', **models):
            for model in models.values():
                model.objects.values_list.return_value = []
            report = audit_databases(database)
            self.assertFalse(has_differences(report))
            models['Usuario'].objects.values_list.assert_called_once_with('pk', 'rolid_id')
            for model in models.values():
                model.objects.all.assert_not_called()
        for collection in collections.values():
            collection.find.assert_called_once()
            projection = collection.find.call_args.args[1]
            self.assertNotIn('password_hash', projection)
            self.assertNotIn('contrasena', projection)
            self.assertNotIn('correo', projection)
            self.assertEqual([call[0] for call in collection.method_calls], ['find'])
