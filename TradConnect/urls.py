# TradConnect/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Catálogos (públicos)
router.register(r'categorias', views.CategoriaViewSet, basename='categoria')
router.register(r'departamentos', views.DepartamentoViewSet, basename='departamento')
router.register(r'municipios', views.MunicipioViewSet, basename='municipio')
router.register(r'estados-pedido', views.EstadoPedidoViewSet, basename='estado-pedido')
router.register(r'metodos-pago', views.MetodoPagoViewSet, basename='metodo-pago')
router.register(r'monedas', views.MonedaViewSet, basename='moneda')
router.register(r'unidades-medida', views.UnidadMedidaViewSet, basename='unidad-medida')

# Empresas y sucursales
router.register(r'empresas', views.EmpresaViewSet, basename='empresa')
router.register(r'sucursales', views.SucursalViewSet, basename='sucursal')

# Marketplace
router.register(r'marketplace', views.MarketplaceViewSet, basename='marketplace')

# Productos e inventario
router.register(r'productos', views.ProductoViewSet, basename='producto')
router.register(r'inventario', views.InventarioBodegaViewSet, basename='inventario')
router.register(r'promociones', views.PromocionViewSet, basename='promocion')

# Pedidos y facturas
router.register(r'pedidos', views.PedidoViewSet, basename='pedido')
router.register(r'detalles-pedido', views.DetallePedidoViewSet, basename='detalle-pedido')
router.register(r'facturas', views.FacturaViewSet, basename='factura')
router.register(r'historial-estado', views.HistorialEstadoPedidoViewSet, basename='historial-estado')

# Documentos
router.register(r'documentos-sucursal', views.DocumentoSucursalViewSet, basename='documento-sucursal')

# Dashboard proveedor
router.register(r'provider-dashboard', views.ProviderDashboardViewSet, basename='provider-dashboard')

urlpatterns = [
    path('', include(router.urls)),
    
    # Rutas manuales de autenticación
    path('auth/register/', views.AuthViewSet.as_view({'post': 'register', 'options': 'register'}), name='register'),
    path('auth/login/', views.AuthViewSet.as_view({'post': 'login', 'options': 'login'}), name='login'),
    path('auth/me/', views.AuthViewSet.as_view({'get': 'me', 'options': 'me'}), name='me'),
    path('auth/update_profile/', views.AuthViewSet.as_view({'put': 'update_profile', 'options': 'update_profile'}), name='update_profile'),
]