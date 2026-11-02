from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from TradConnect.sql_models import SqlPedido as Pedido, SqlMoneda as Moneda
from TradConnect.identities import company_names
from config.mongodb import get_database
from .customer_views import company
from .views import DocumentView
from django.core.exceptions import ImproperlyConfigured
from pymongo.errors import PyMongoError


class ProviderAnalyticsView(DocumentView):
    permission_classes = [IsAuthenticated]
    provider = True

    def get(self, request):
        owner = company(request, provider=self.provider)
        try:
            start = date.fromisoformat(request.query_params.get('start', '2000-01-01'))
            end = date.fromisoformat(request.query_params.get('end', timezone.localdate().isoformat()))
            currency = int(request.query_params.get('moneda', '0'))
        except (ValueError, TypeError):
            raise ValidationError('Fechas o moneda inv?lidas.')
        if end == date.max:
            raise ValidationError("La fecha final debe ser anterior a 9999-12-31.")
        if start > end:
            raise ValidationError('El inicio debe ser anterior al final.')
        currencies = list(Moneda.objects.values('id', 'nombremoneda'))
        if not currency and currencies:
            currency = currencies[0]['id']
        if currency not in [item['id'] for item in currencies]:
            raise ValidationError('Selecciona una moneda v?lida.')
        scope_field = 'proveedorid' if self.provider else 'restauranteid'
        partner_field = 'restauranteid' if self.provider else 'proveedorid'
        orders = Pedido.objects.filter(**{scope_field: owner.pk}, monedaid_id=currency,
            fechapedido__date__gte=start, fechapedido__date__lte=end).select_related('estadopedidoid').prefetch_related('sqldetallepedido_set__productoid__categoriaid')
        names=company_names({getattr(order,partner_field) for order in orders})
        months, states, products, categories, clients = {}, defaultdict(int), {}, {}, {}
        total = Decimal('0'); count = 0; quantity = Decimal('0')
        for order in orders:
            state = order.estadopedidoid.estadonombre
            states[state] += 1
            if state.casefold() in ('cancelado', 'cancelada'):
                continue
            total += order.totalneto; count += 1
            month = timezone.localtime(order.fechapedido).strftime('%Y-%m')
            row = months.setdefault(month, {'fecha__fecha': month, 'total_ventas': Decimal('0'), 'total_pedidos': 0, 'cantidad_items': Decimal('0')})
            row['total_ventas'] += order.totalneto; row['total_pedidos'] += 1
            partner = getattr(order, partner_field)
            client = clients.setdefault(partner, {'empresa__razon_social': names.get(partner,'Empresa'),
                'empresa__ruc': '', 'total_comprado': Decimal('0'), 'total_pedidos': 0})
            client['total_comprado'] += order.totalneto; client['total_pedidos'] += 1
            for detail in order.sqldetallepedido_set.all():
                amount = detail.subtotallinea
                quantity += detail.cantidad; row['cantidad_items'] += detail.cantidad
                product = products.setdefault(detail.productoid_id, {'producto__nombre_producto': detail.productoid.nombreproducto, 'total_vendido': Decimal('0'), 'total_ingreso': Decimal('0')})
                product['total_vendido'] += detail.cantidad; product['total_ingreso'] += amount
                category = categories.setdefault(detail.productoid.categoriaid_id, {'producto__categoria': detail.productoid.categoriaid.nombrecategoria, 'total_ingreso': Decimal('0'), 'total_cantidad': Decimal('0')})
                category['total_ingreso'] += amount; category['total_cantidad'] += detail.cantidad
        feedback = {'disponible': False}
        try:
            scope = {('proveedor_empresa_id' if self.provider else 'cliente_empresa_id'): str(owner.pk), 'fecha': {'$gte': start.isoformat(), '$lt': (end + timedelta(days=1)).isoformat()}}
            db = get_database()
            reviews = list(db['evaluaciones_proveedores'].find(scope, {'puntuacion': 1}))
            feedback = {'disponible': True, 'evaluaciones': len(reviews),
                'puntuacion': sum(r['puntuacion'] for r in reviews) / len(reviews) if reviews else None,
                'reclamos': db['incidencias_entregas'].count_documents(scope),
                'pendientes': db['incidencias_entregas'].count_documents({**scope, 'estado': 'Pendiente'}),
                'resueltos': db['incidencias_entregas'].count_documents({**scope, 'estado': 'Resuelta'})}
        except (PyMongoError, ImproperlyConfigured):
            pass
        return Response({'monedas': currencies, 'moneda': currency,
            'ventas': [months[key] for key in sorted(months)],
            'estados': [{'estado_pedido__estado_nombre': key, 'cantidad_pedidos': value} for key, value in states.items()],
            'productos': sorted(products.values(), key=lambda r: r['total_ingreso'], reverse=True)[:5],
            'categorias': list(categories.values()), 'clientes': list(clients.values()), 'feedback': feedback})


class CustomerAnalyticsView(ProviderAnalyticsView):
    provider = False
