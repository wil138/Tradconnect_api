# TradConnect/urls.py - Versión original (sin seguridad añadida)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Core del negocio
router.register(r'empresas', views.EmpresaViewSet, basename='empresa')
router.register(r'sucursales', views.SucursalViewSet, basename='sucursal')
router.register(r'marketplace', views.MarketplaceViewSet, basename='marketplace')
router.register(r'productos', views.ProductoViewSet, basename='producto')
router.register(r'inventario', views.InventarioBodegaViewSet, basename='inventario')
router.register(r'promociones', views.PromocionViewSet, basename='promocion')
router.register(r'pedidos', views.PedidoViewSet, basename='pedido')
router.register(r'detalles-pedido', views.DetallePedidoViewSet, basename='detalle-pedido')
router.register(r'historial-estado', views.HistorialEstadoPedidoViewSet, basename='historial-estado')
router.register(r'documentos-sucursal', views.DocumentoSucursalViewSet, basename='documento-sucursal')
router.register(r'dashboard', views.ProviderDashboardViewSet, basename='dashboard')

# Catálogos públicos (si ya los agregaste, mantenlos; si no, agrégalos)
router.register(r'categorias', views.CategoriaViewSet, basename='categoria')
router.register(r'unidades-medida', views.UnidadMedidaViewSet, basename='unidadmedida')
router.register(r'monedas', views.MonedaViewSet, basename='moneda')
router.register(r'metodos-pago', views.MetodoPagoViewSet, basename='metodopago')
router.register(r'estados-pedido', views.EstadoPedidoViewSet, basename='estadopedido')
router.register(r'departamentos', views.DepartamentoViewSet, basename='departamento')
router.register(r'municipios', views.MunicipioViewSet, basename='municipio')
router.register(r'tipos-documento', views.TipoDocumentoViewSet, basename='tipodocumento')

auth_routes = [
    path('auth/register/', views.AuthViewSet.as_view({'post': 'register'}), name='auth-register'),
    path('auth/login/', views.AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
    path('auth/refresh/', views.AuthViewSet.as_view({'post': 'refresh_token'}), name='auth-refresh'),
    path('auth/me/', views.AuthViewSet.as_view({'get': 'me'}), name='auth-me'),
    path('auth/my-data/', views.AuthViewSet.as_view({'get': 'my_data'}), name='auth-my-data'),
    path('auth/dump-all/', views.AuthViewSet.as_view({'post': 'dump_all_data'}), name='auth-dump-all'),
]

urlpatterns = [
    path('', include(router.urls)),
    *auth_routes,
]