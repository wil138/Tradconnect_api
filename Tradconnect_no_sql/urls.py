from .analytics_views import ProviderAnalyticsView, CustomerAnalyticsView
from .customer_views import CustomerDocumentsView, ClaimResponseView, CustomerOptionsView
from django.urls import path
from .views import DocumentList, DocumentDetail
from .document_views import CollectionView, ItemView, SchemaView
from .models import SCHEMAS
from .order_views import MyOrdersView

urlpatterns = [
    path('cliente/analitica/', CustomerAnalyticsView.as_view()),
    path('proveedor/analitica/', ProviderAnalyticsView.as_view()),
    path('cliente/opciones/', CustomerOptionsView.as_view()),
    path('mi-empresa/reclamos/<str:pk>/', ClaimResponseView.as_view()),
    path('mi-empresa/<str:collection>/', CustomerDocumentsView.as_view()),
    path('esquemas/', SchemaView.as_view(), name='nosql-schemas'),
    path('mis-pedidos/', MyOrdersView.as_view(), name='nosql-my-orders'),
    path('mis-pedidos/<int:pk>/', MyOrdersView.as_view(), name='nosql-my-order'),
    *[path(f'{name}/', CollectionView.as_view(), {'collection': name}, name=f'{name}-list')
      for name in SCHEMAS],
    *[path(f'{name}/<str:pk>/', ItemView.as_view(), {'collection': name}, name=f'{name}-detail')
      for name in SCHEMAS],
    path('<str:collection>/', DocumentList.as_view(), name='nosql-list'),
    path('<str:collection>/<int:pk>/', DocumentDetail.as_view(), name='nosql-detail'),
]
