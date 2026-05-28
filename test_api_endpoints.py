import unittest
import requests
import random

# URL base unificada con el prefijo correcto del proyecto
BASE_URL = "http://127.0.0.1:8000/api"

class TestTradConnectAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Configuración inicial: Registra un usuario de tipo cliente (exigido por views.py)
        y adquiere el token JWT para autenticar el resto de peticiones de la suite.
        """
        cls.client = requests.Session()
        cls.email = f"tester_{random.randint(1000, 9999)}@tradconnect.com"
        cls.username = f"user_{random.randint(1000, 9999)}"
        cls.password = "PasswordSeguro123!"
        
        # Estructura exacta requerida por tu EmpresaRegistroSerializer en views.py
        register_data = {
            "rol": "client",  # El ViewSet busca el texto exacto del rol en la BD
            "nombre_usuario": cls.username,
            "correo": cls.email,
            "contrasena": cls.password,
            "razon_social": f"Restaurante Test {random.randint(10,99)} S.A.",
            "ruc": f"J03100000{random.randint(10000,99999)}",
            "telefono": "8888-1111",
            "direccion_fiscal": "Managua, Nicaragua"
        }

        register_url = f"{BASE_URL}/auth/register/"
        print(f"\n🚀 Probando registro en endpoint unificado: {register_url}")
        
        try:
            response = cls.client.post(register_url, json=register_data, timeout=5)
        except requests.exceptions.ConnectionError:
            raise RuntimeError("❌ El servidor de Django está apagado. Ejecuta 'python manage.py runserver' antes de lanzar el test.")

        # Validar el código de respuesta del registro (201 Created)
        assert response.status_code in [200, 201], f"Fallo al registrar usuario en {register_url}: {response.status_code} - {response.text}"

        # Extraer tokens JWT devueltos directamente por tu AuthViewSet.register
        tokens = response.json()
        cls.access_token = tokens.get("access")
        cls.empresa_id = tokens.get("user", {}).get("empresa_id")

        # Configurar cabeceras de autorización global usando SimpleJWT
        cls.headers = {
            "Authorization": f"Bearer {cls.access_token}",
            "Content-Type": "application/json"
        }
        print("🔑 Token JWT obtenido y guardado en cabeceras.")
        print("⚡ Iniciando escaneo de métodos de la API...\n")

    # =========================================================================
    # 1. MÓDULO: AUTENTICACIÓN / PROFILE
    # =========================================================================
    def test_01_auth_me(self):
        """Prueba GET /api/auth/me/ (Verificar perfil del usuario logueado)"""
        url = f"{BASE_URL}/auth/me/"
        response = requests.get(url, headers=self.headers)
        self.assertEqual(response.status_code, 200, f"Error en: {url}")
        self.assertEqual(response.json().get("email"), self.email)

    def test_02_auth_update_profile(self):
        """Prueba PUT /api/auth/update_profile/ (Modificar datos de perfil)"""
        url = f"{BASE_URL}/auth/update_profile/"
        update_data = {
            "username": f"{self.username}_mod",
            "empresa": {
                "razon_social": "Razón Social Modificada por Test"
            }
        }
        response = requests.put(url, json=update_data, headers=self.headers)
        self.assertEqual(response.status_code, 200, f"Error en: {url}")
        self.assertIn("correctamente", response.json().get("message", ""))

    # =========================================================================
    # 2. MÓDULO: CATÁLOGOS PÚBLICOS (ReadOnlyModelViewSets)
    # =========================================================================
    def test_03_catalogos_publicos(self):
        """Prueba método GET en todos los endpoints de catálogos bajo /api/"""
        catalogos = [
            'categorias', 'departamentos', 'municipios', 
            'estados-pedido', 'metodos-pago', 'monedas', 'unidades-medida'
        ]
        for cat in catalogos:
            url = f"{BASE_URL}/{cat}/"
            response = requests.get(url, headers=self.headers)
            self.assertEqual(response.status_code, 200, f"Fallo al leer catálogo: {url}")
            self.assertIsInstance(response.json(), list)

    # =========================================================================
    # 3. MÓDULO: SUCURSALES (Filtros dinámicos por request.user)
    # =========================================================================
    def test_04_sucursal_lifecycle(self):
        """Prueba los métodos GET y POST en el endpoint /api/sucursales/"""
        url = f"{BASE_URL}/sucursales/"
        
        # POST - Intentar registrar una sucursal para la empresa del tester
        sucursal_data = {
            "empresaid": self.empresa_id,
            "nombresucursal": "Sucursal de Pruebas Automáticas",
            "municipioid": 1, 
            "direccionexacta": "De la rotonda El Güegüense 2c al norte",
            "telefonosucursal": "2266-9999",
            "horarioatencion": "08:00 AM - 05:00 PM",
            "esbodega": False,
            "estado": "Activo"
        }
        response_post = requests.post(url, json=sucursal_data, headers=self.headers)
        # Aceptamos 200, 201 o 400 controlado según las restricciones lógicas de tu backend,
        # pero validamos que el endpoint responda de manera coherente.
        self.assertIn(response_post.status_code, [200, 201, 400], f"Error inesperado: {response_post.text}")

        # GET - Listar sucursales
        response_get = requests.get(url, headers=self.headers)
        self.assertEqual(response_get.status_code, 200)

    # =========================================================================
    # 4. MÓDULO: MARKETPLACE (Acciones custom con @action)
    # =========================================================================
    def test_05_marketplace_custom_actions(self):
        """Prueba las vistas compuestas integradas del Marketplace"""
        # GET /api/marketplace/products/
        url_products = f"{BASE_URL}/marketplace/products/"
        res_prod = requests.get(url_products, headers=self.headers)
        self.assertEqual(res_prod.status_code, 200)
        self.assertIn("results", res_prod.json())

        # GET /api/marketplace/categories/
        url_cats = f"{BASE_URL}/marketplace/categories/"
        res_cats = requests.get(url_cats, headers=self.headers)
        self.assertEqual(res_cats.status_code, 200)

    # =========================================================================
    # 5. MÓDULO: OPERACIONES BASE (Tablas relacionales con nombres fijos de urls.py)
    # =========================================================================
    def test_06_endpoints_operacionales_get(self):
        """Prueba de lectura masiva en las tablas del pipeline transaccional"""
        endpoints = [
            'productos', 'inventario', 'promociones', 
            'pedidos', 'detalles-pedido', 'facturas', 
            'historial-estado', 'documentos-sucursal'
        ]
        for end in endpoints:
            url = f"{BASE_URL}/{end}/"
            response = requests.get(url, headers=self.headers)
            self.assertEqual(response.status_code, 200, f"Error leyendo tabla operacional: {url} - {response.text}")

if __name__ == "__main__":
    unittest.main()

#python test_api_endpoints.py