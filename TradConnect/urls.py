# TradConnect/urls.py - Versión original (sin seguridad añadida)
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import hybrid_views as views
from . import sql_models as m
from rest_framework.permissions import AllowAny

router = DefaultRouter()
router.register(r'dashboard', views.DashboardViewSet, basename='dashboard')

# Core del negocio
router.register(r'empresas', views.CompanyViewSet, basename='empresa')
router.register(r'sucursales', views.BranchViewSet, basename='sucursal')
router.register(r'marketplace', views.MarketplaceViewSet, basename='marketplace')
router.register(r'productos', views.ProductViewSet, basename='producto')
router.register(r'inventario', views.InventoryViewSet, basename='inventario')
router.register(r'promociones', views.PromotionViewSet, basename='promocion')
router.register(r'pedidos', views.OrderViewSet, basename='pedido')
router.register(r'detalles-pedido', views.DetailViewSet, basename='detalle-pedido')
router.register(r'documentos-sucursal', views.DocumentsViewSet, basename='documento-sucursal')

# Catálogos públicos (si ya los agregaste, mantenlos; si no, agrégalos)
router.register(r'categorias', views.catalog_view(m.SqlCategoria), basename='categoria')
router.register(r'unidades-medida', views.catalog_view(m.SqlUnidadmedida), basename='unidadmedida')
router.register(r'monedas', views.catalog_view(m.SqlMoneda), basename='moneda')
router.register(r'metodos-pago', views.catalog_view(m.SqlMetodopago), basename='metodopago')
router.register(r'estados-pedido', views.catalog_view(m.SqlEstadopedido), basename='estadopedido')
router.register(r'departamentos', views.catalog_view(m.SqlDepartamento), basename='departamento')
router.register(r'municipios', views.catalog_view(m.SqlMunicipio), basename='municipio')
router.register(r'tipos-documento', views.catalog_view(m.SqlTipodocumento), basename='tipodocumento')

auth_routes = [
    path('auth/register/', views.AuthViewSet.as_view({'post': 'register'}, authentication_classes=[], permission_classes=[AllowAny]), name='auth-register'),
    path('auth/login/', views.AuthViewSet.as_view({'post': 'login'}, authentication_classes=[], permission_classes=[AllowAny]), name='auth-login'),
    path('auth/refresh/', views.AuthViewSet.as_view({'post': 'refresh_token'}, authentication_classes=[], permission_classes=[AllowAny]), name='auth-refresh'),
    path('auth/me/', views.AuthViewSet.as_view({'get': 'me'}), name='auth-me'),
    path('auth/my-data/', views.AuthViewSet.as_view({'get': 'my_data'}), name='auth-my-data'),
    path('auth/dump-all/', views.AuthViewSet.as_view({'post': 'dump_all_data'}, authentication_classes=[], permission_classes=[AllowAny]), name='auth-dump-all'),
    path('auth/change-password/', views.AuthViewSet.as_view({'post': 'change_password'}), name='auth-change-password'),
    path('auth/update-profile/', views.AuthViewSet.as_view({'put': 'update_profile'}), name='auth-update-profile'),
]

urlpatterns = [
    path('', include(router.urls)),
    *auth_routes,
]
