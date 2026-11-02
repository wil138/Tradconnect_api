"""Precios y stock calculados por el servidor, compartidos por cotizacion y compra."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound
from . import sql_models as m
from .identities import company

MONEY=Decimal('.01')


def decimal(value,name):
    try:
        number=Decimal(str(value))
    except (InvalidOperation,ValueError,TypeError):
        raise ValidationError({name:'Numero invalido.'})
    if not number.is_finite(): raise ValidationError({name:'Numero invalido.'})
    return number


def prepare_order(request, lock=False):
    buyer=company(request,provider=False)
    body=request.data
    if not isinstance(body,dict): raise ValidationError('Se requiere un objeto JSON.')
    try:
        origin=int(body['sucursal_origen_id']); destination=int(body['sucursal_entrega_id'])
        method=int(body['metodo_pago_id']); currency=int(body['moneda_id'])
        seller=str(body['proveedor_id'])
    except (KeyError,TypeError,ValueError):
        raise ValidationError('Selecciona proveedor, sucursales, moneda y metodo de pago.')
    if currency!=getattr(settings,'MARKETPLACE_CURRENCY_ID',1):
        raise ValidationError('La moneda no coincide con la moneda del catalogo; no se convierten divisas.')
    if not m.SqlMoneda.objects.filter(pk=currency).exists() or not m.SqlMetodopago.objects.filter(pk=method).exists():
        raise ValidationError('Moneda o metodo de pago inexistente.')
    if not m.SqlSucursal.objects.filter(pk=destination,empresaid=buyer.pk,estado__in=['Activo','Activa']).exists():
        raise ValidationError('La sucursal de entrega no pertenece a tu empresa o esta inactiva.')
    if not m.SqlSucursal.objects.filter(pk=origin,empresaid=seller,estado__in=['Activo','Activa']).exists():
        raise ValidationError('La sucursal de origen no pertenece al proveedor o esta inactiva.')
    items=body.get('items')
    if not isinstance(items,list) or not 1<=len(items)<=100:
        raise ValidationError('Selecciona entre 1 y 100 productos.')
    quantities={}
    for item in items:
        if not isinstance(item,dict): raise ValidationError('Producto invalido.')
        try: product_id=int(item['producto_id'])
        except (KeyError,TypeError,ValueError): raise ValidationError('Producto invalido.')
        quantity=decimal(item.get('cantidad'),'cantidad')
        if quantity<=0 or quantity!=quantity.quantize(MONEY,rounding=ROUND_HALF_UP) or quantity>Decimal('9999999999.99'):
            raise ValidationError('La cantidad debe ser positiva y tener hasta dos decimales.')
        quantities[product_id]=quantities.get(product_id,Decimal(0))+quantity
    lines=[]; inventory=[]
    for product_id,quantity in sorted(quantities.items()):
        product=m.SqlProducto.objects.filter(pk=product_id,empresaid=seller,eliminado=False).first()
        if product is None: raise ValidationError('El producto no pertenece al proveedor.')
        if quantity<product.cantidadminimapedido: raise ValidationError('No se cumple la cantidad minima del producto.')
        query=m.SqlInventariobodega.objects.filter(productoid=product,sucursalid_id=origin).order_by('pk')
        if lock: query=query.select_for_update()
        stocks=list(query)
        if len(stocks)!=1: raise ValidationError('El producto no tiene un unico registro de stock para esa sucursal.')
        stock=stocks[0]
        if stock.stockdisponible<quantity: raise ValidationError('Stock insuficiente.')
        promotions=m.SqlPromocion.objects.filter(productoid=product,fechainicio__lte=timezone.localdate(),
            fechafin__gte=timezone.localdate(),cantidadminima__lte=quantity)
        discount=max([p.porcentajedescuento for p in promotions] or [Decimal(0)])
        if not 0<=discount<=100: raise ValidationError('Promocion invalida.')
        gross=(product.precioventa*quantity).quantize(MONEY,rounding=ROUND_HALF_UP)
        saving=(gross*discount/100).quantize(MONEY,rounding=ROUND_HALF_UP)
        net=gross-saving
        tax=(net*Decimal('.15')).quantize(MONEY,rounding=ROUND_HALF_UP)
        lines.append({'producto_id':product_id,'nombre':product.nombreproducto,'cantidad':quantity,'precio_unitario':product.precioventa,
            'descuento_porcentaje':discount,'monto_descuento':saving,'subtotal':net,'impuesto':tax,'total':net+tax})
        inventory.append(stock)
    quote={'subtotal':sum(line['subtotal'] for line in lines),'ahorro':sum(line['monto_descuento'] for line in lines),
        'impuesto':sum(line['impuesto'] for line in lines),'totalneto':sum(line['total'] for line in lines),
        'moneda_id':currency,'detalles':lines}
    return buyer,seller,origin,destination,method,quote,inventory


@transaction.atomic
def create_order(request):
    buyer,seller,origin,destination,method,quote,stocks=prepare_order(request,lock=True)
    try:
        signed=signing.loads(request.data.get('quote_token',''),salt='checkout',max_age=300)
    except signing.BadSignature:
        raise ValidationError('Cotiza de nuevo el pedido antes de confirmar.')
    expected=quote_payload(buyer,seller,origin,destination,method,quote)
    if signed!=expected:
        raise ValidationError('Los precios cambiaron. Revisa y confirma una nueva cotizacion.')
    state=m.SqlEstadopedido.objects.filter(estadonombre__iexact='Pendiente').first()
    if state is None: raise ValidationError('Falta el estado Pendiente en SQL.')
    order=m.SqlPedido.objects.create(restauranteid=buyer.pk,proveedorid=seller,sucursaloriginalid_id=origin,
        sucursalentregaid_id=destination,monedaid_id=quote['moneda_id'],metodopagoid_id=method,estadopedidoid=state,
        subtotal=quote['subtotal'],impuesto=quote['impuesto'],totalneto=quote['totalneto'],
        comentario=str(request.data.get('comentario',''))[:500],fechapedido=timezone.now())
    for line,stock in zip(quote['detalles'],stocks):
        m.SqlDetallepedido.objects.create(pedidoid=order,productoid_id=line['producto_id'],cantidad=line['cantidad'],
            preciounitario=line['precio_unitario'],montodescuento=line['monto_descuento'],subtotallinea=line['subtotal'],
            impuestolinea=line['impuesto'],totalnetolinea=line['total'])
        stock.stockdisponible-=line['cantidad']; stock.ultimaactualizacion=timezone.now()
        stock.save(update_fields=['stockdisponible','ultimaactualizacion'])
    return order


def quote_payload(buyer,seller,origin,destination,method,quote):
    return json.loads(json.dumps({'buyer':buyer.pk,'seller':seller,'origin':origin,'destination':destination,'method':method,'quote':quote},cls=DjangoJSONEncoder))


def quote_order(request):
    buyer,seller,origin,destination,method,quote,_=prepare_order(request)
    quote['quote_token']=signing.dumps(quote_payload(buyer,seller,origin,destination,method,dict(quote)),salt='checkout',compress=True)
    return quote
