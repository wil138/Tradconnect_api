from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from TradConnect.identities import Principal, resolve, authenticate_credentials, company
from types import SimpleNamespace


class HybridIdentityTests(SimpleTestCase):
    def doc(self,**changes):
        return dict({'usuario_id':'usr_a','empresa_id':'emp_a','nombre_rol':'Cliente','estado_usuario':True,'estado_rol':True,'auth_version':2,'password_hash':'hidden'},**changes)

    @patch('TradConnect.identities.users')
    def test_jwt_version_must_match_database(self,users):
        users.return_value.find_one.return_value=self.doc()
        with self.assertRaises(AuthenticationFailed): resolve('usr_a','emp_a',1)
        self.assertEqual(resolve('usr_a','emp_a',2).company_id,'emp_a')
        self.assertEqual(users.return_value.find_one.call_args.args[0]['estado_usuario'],True)

    @patch('TradConnect.identities.check_password',return_value=True)
    @patch('TradConnect.identities.users')
    def test_inactive_account_cannot_login_with_correct_password(self,users,password):
        users.return_value.find.return_value.sort.return_value=[self.doc(estado_usuario=False)]
        with self.assertRaises(PermissionDenied): authenticate_credentials('ana','correct-password')

    def test_admin_cannot_use_customer_or_provider_company_flow(self):
        request=SimpleNamespace(user=Principal(self.doc(nombre_rol='Admin')))
        with self.assertRaises(PermissionDenied): company(request,provider=False)
        with self.assertRaises(PermissionDenied): company(request,provider=True)

    @patch('TradConnect.identities.users')
    def test_ambiguous_login_is_rejected(self,users):
        users.return_value.find.return_value.sort.return_value=[self.doc(),self.doc(usuario_id='usr_b')]
        with self.assertRaises(AuthenticationFailed): authenticate_credentials('ana','password')
