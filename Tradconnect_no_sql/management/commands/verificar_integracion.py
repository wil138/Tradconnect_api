"""Prueba con cuentas temporales; revierte SQL y elimina sus documentos MongoDB."""
import json
from uuid import uuid4
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient
from config.mongodb import get_database
from TradConnect import sql_models as m


class Command(BaseCommand):
    help='Verifica flujos completos contra SQL Server y MongoDB sin conservar datos de prueba.'
    def handle(self,*args,**options):
        db=get_database(); marker=uuid4().hex; ids=[]; companies=[]; checks=[]
        def check(name,condition):
            if not condition: raise CommandError('Fallo de integracion: '+name)
            checks.append(name)
        def call(client,method,path,data=None,status=200):
            response=getattr(client,method)(path,data or {},format='json')
            if response.status_code!=status:
                detail=str(response.data.get('detail','')) if isinstance(getattr(response,'data',None),dict) else ''
                raise CommandError(f'{method.upper()} {path}: HTTP {response.status_code}, esperado {status}. '+detail)
            return response.data
        try:
            with transaction.atomic():
                try:
                    clients=[]
                    for role in ('restaurant','provider'):
                        client=APIClient(); name='verify_'+role+'_'+marker
                        body={'nombre_usuario':name,'correo':name+'@example.com','contrasena':'Integration!42Long','rol':role,
                            'razon_social':'Verificacion temporal','ruc':'V'+uuid4().hex,'telefono':'00000000'}
                        call(client,'post','/api/auth/register/',body,201)
                        doc=db.usuarios_empresas_roles.find_one({'nombre_usuario':name}); ids.append(doc['usuario_id']); companies.append(doc['empresa_id'])
                        data=call(client,'post','/api/auth/login/',{'username':body['correo'],'password':body['contrasena']})
                        check('login_'+role,'tokens' in data and 'password_hash' not in json.dumps(data,default=str))
                        client.credentials(HTTP_AUTHORIZATION='Bearer '+data['tokens']['access']); clients.append(client)
                    buyer,seller=clients
                    municipality=m.SqlMunicipio.objects.first(); category=m.SqlCategoria.objects.first(); unit=m.SqlUnidadmedida.objects.first(); payment=m.SqlMetodopago.objects.first()
                    branches=[call(client,'post','/api/sucursales/',{'nombresucursal':'Verificacion temporal','municipioid':municipality.pk,'direccionexacta':'Temporal','estado':'Activo'},201) for client in clients]
                    product=call(seller,'post','/api/productos/',{'nombreproducto':'Verificacion '+marker,'categoriaid':category.pk,'unidadmedidaid':unit.pk,
                        'precioventa':'10.00','cantidadminimapedido':1,'stock_inicial':'10.50','sucursal_id':branches[1]['id']},201)
                    call(buyer,'get','/api/productos/'+str(product['id'])+'/',status=403)
                    call(buyer,'get','/api/sucursales/'+str(branches[1]['id'])+'/',status=404)
                    call(buyer,'patch','/api/empresas/'+companies[1]+'/',{'razonsocial':'Ajena'},404)
                    check('permisos_empresa',True)
                    call(seller,'post','/api/promociones/',{'productoid':product['id'],'cantidadminima':1,'porcentajedescuento':'10.00',
                        'fechainicio':timezone.localdate().isoformat(),'fechafin':timezone.localdate().isoformat()},201)
                    payload={'proveedor_id':companies[1],'sucursal_origen_id':branches[1]['id'],'sucursal_entrega_id':branches[0]['id'],
                        'metodo_pago_id':payment.pk,'moneda_id':getattr(settings,'MARKETPLACE_CURRENCY_ID',1),
                        'items':[{'producto_id':product['id'],'cantidad':'1.50','precio_unitario':'0.01','descuento':99}]}
                    call(buyer,'post','/api/pedidos/cotizar/',{**payload,'items':[{'producto_id':product['id'],'cantidad':'999'}]},400)
                    check('stock_insuficiente_rechazado',m.SqlInventariobodega.objects.get(productoid_id=product['id'],sucursalid_id=branches[1]['id']).stockdisponible==Decimal('10.50'))
                    call(seller,'patch','/api/productos/'+str(product['id'])+'/',{'precioventa':'11.00','stock_disponible':'4','sucursal_id':branches[0]['id']},400)
                    check('producto_stock_atomicos',m.SqlProducto.objects.get(pk=product['id']).precioventa==Decimal('10.00'))
                    quote=call(buyer,'post','/api/pedidos/cotizar/',payload)
                    check('cantidad_decimal_descuento_iva',Decimal(quote['subtotal'])==Decimal('13.50') and Decimal(quote['impuesto'])==Decimal('2.03') and Decimal(quote['totalneto'])==Decimal('15.53'))
                    call(buyer,'post','/api/pedidos/',payload,400)
                    m.SqlProducto.objects.filter(pk=product['id']).update(precioventa=Decimal('11.00'))
                    call(buyer,'post','/api/pedidos/',{**payload,'quote_token':quote['quote_token']},400)
                    check('cotizacion_antigua_rechazada',m.SqlPedido.objects.filter(restauranteid=companies[0]).count()==0)
                    m.SqlProducto.objects.filter(pk=product['id']).update(precioventa=Decimal('10.00'))
                    order=call(buyer,'post','/api/pedidos/',{**payload,'quote_token':quote['quote_token']},201)
                    check('importe_confirmado',Decimal(order['totalneto'])==Decimal(quote['totalneto']))
                    stock=m.SqlInventariobodega.objects.get(productoid_id=product['id'],sucursalid_id=branches[1]['id'])
                    check('stock_descontado',stock.stockdisponible==Decimal('9.00'))
                    claim=call(buyer,'post','/api/nosql/mi-empresa/incidencias_entregas/',{'pedido_id_sql':order['id'],'tipo_incidencia':'Verificacion','tipo_reclamo':'Temporal'},201)
                    call(seller,'patch','/api/nosql/mi-empresa/reclamos/'+claim['_id']+'/',{'estado':'Resuelta','respuesta_proveedor':'Verificacion temporal'})
                    check('reclamo_resuelto',db.incidencias_entregas.find_one({'_id':claim['_id']})['estado']=='Resuelta')
                    analytics=call(seller,'get','/api/nosql/proveedor/analitica/')
                    check('analitica_real',len(analytics['ventas'])==1)
                    cancelled=m.SqlEstadopedido.objects.filter(estadonombre__iexact='Cancelado').first()
                    if cancelled:
                        call(seller,'put','/api/pedidos/'+str(order['id'])+'/update_status/',{'estado_id':cancelled.pk})
                        call(seller,'put','/api/pedidos/'+str(order['id'])+'/update_status/',{'estado_id':cancelled.pk})
                        stock.refresh_from_db(); check('cancelacion_reintegra_stock_una_vez',stock.stockdisponible==Decimal('10.50'))
                    call(buyer,'put','/api/auth/update-profile/',{'nombreusuario':'verify_updated_'+marker,'telefono':'00000000'})
                    first=call(buyer,'post','/api/nosql/mi-empresa/preferencias_negocio/',{'horario_entrega_preferido':'08:00'},201)
                    second=call(buyer,'post','/api/nosql/mi-empresa/preferencias_negocio/',{'horario_entrega_preferido':'09:00'},201)
                    check('preferencias_sin_duplicar',first['_id']==second['_id'] and db.preferencias_negocio.count_documents({'empresa_id':companies[0]})==1)
                    check('perfil_guardado',db.usuarios_empresas_roles.find_one({'usuario_id':ids[0]})['nombre_usuario']=='verify_updated_'+marker)
                    changed=call(buyer,'post','/api/auth/change-password/',{'old_password':'Integration!42Long','new_password':'Changed!93Strong'})
                    call(buyer,'get','/api/auth/my-data/',status=401)
                    buyer.credentials(HTTP_AUTHORIZATION='Bearer '+changed['tokens']['access']); call(buyer,'get','/api/auth/my-data/')
                    check('password_revoca_jwt',True)
                    self.stdout.write(json.dumps({'checks':checks,'total':len(checks),'sql_rollback':True}))
                finally: transaction.set_rollback(True)
        finally:
            if ids: db.usuarios_empresas_roles.delete_many({'usuario_id':{'$in':ids}})
            if companies:
                for name,field in [('incidencias_entregas','cliente_empresa_id'),('preferencias_negocio','empresa_id')]:
                    db[name].delete_many({field:{'$in':companies}})
