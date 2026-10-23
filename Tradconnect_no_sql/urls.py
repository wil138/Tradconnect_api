from django.urls import path
from .views import DocumentList, DocumentDetail
from .document_views import CollectionView, ItemView
from .models import SCHEMAS
from .order_views import MyOrdersView

urlpatterns = [
    path('mis-pedidos/', MyOrdersView.as_view(), name='nosql-my-orders'),
    path('mis-pedidos/<int:pk>/', MyOrdersView.as_view(), name='nosql-my-order'),
    *[path(f'{name}/', CollectionView.as_view(), {'collection': name}, name=f'{name}-list')
      for name in SCHEMAS],
    *[path(f'{name}/<str:pk>/', ItemView.as_view(), {'collection': name}, name=f'{name}-detail')
      for name in SCHEMAS],
    path('<str:collection>/', DocumentList.as_view(), name='nosql-list'),
    path('<str:collection>/<int:pk>/', DocumentDetail.as_view(), name='nosql-detail'),
]
