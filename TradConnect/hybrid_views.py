"""API activa: identidades MongoDB y operaciones del esquema SQL real."""
from uuid import uuid4
from decimal import Decimal
from types import SimpleNamespace
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied, AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from . import sql_models as m
from . import identities as identity
from .hybrid_serializers import ProductSerializer, BranchSerializer, InventorySerializer, OrderSerializer, DetailSerializer, model_serializer
from .commerce import create_order, quote_order

CATALOGS={'categorias':m.SqlCategoria,'unidades_medida':m.SqlUnidadmedida,'metodos_pago':m.SqlMetodopago,
    'monedas':m.SqlMoneda,'estados_pedido':m.SqlEstadopedido,'departamentos':m.SqlDepartamento,
    'municipios':m.SqlMunicipio,'tipos_documento':m.SqlTipodocumento}


def object_body(request):
    if not isinstance(request.data,dict): raise ValidationError('Se requiere un objeto JSON.')
    return request.data


def catalog_data():
    return {name:model_serializer(model)(model.objects.order_by('pk'),many=True).data for name,model in CATALOGS.items()}


def product_query():
    from django.db.models import Prefetch
    stocks=m.SqlInventariobodega.objects.select_related('sucursalid')
    return m.SqlProducto.objects.select_related('categoriaid','unidadmedidaid').prefetch_related(
        Prefetch('sqlinventariobodega_set',queryset=stocks), 'sqlpromocion_set')


def order_query():
    return m.SqlPedido.objects.select_related('estadopedidoid').prefetch_related('sqldetallepedido_set__productoid').order_by('-fechapedido','-pk')


def snapshot(principal):
    company_id=principal.company_id
    products=product_query().filter(empresaid=company_id,eliminado=False) if company_id else m.SqlProducto.objects.none()
    branches=m.SqlSucursal.objects.filter(empresaid=company_id) if company_id else m.SqlSucursal.objects.none()
    inventory=m.SqlInventariobodega.objects.filter(sucursalid__empresaid=company_id).select_related('sucursalid','productoid') if company_id else m.SqlInventariobodega.objects.none()
    buyer=order_query().filter(restauranteid=company_id) if company_id else m.SqlPedido.objects.none()
    seller=order_query().filter(proveedorid=company_id) if company_id else m.SqlPedido.objects.none()
    bought=OrderSerializer(buyer,many=True).data; sold=OrderSerializer(seller,many=True).data
    return {'usuario':identity.user_data(principal),'empresa':identity.company_data(principal), 'catalogos':catalog_data(),
        'sucursales':BranchSerializer(branches,many=True).data,'productos':ProductSerializer(products,many=True).data,
        'inventario':InventorySerializer(inventory,many=True).data,
        'promociones':model_serializer(m.SqlPromocion)(m.SqlPromocion.objects.filter(productoid__empresaid=company_id),many=True).data if company_id else [],
        'pedidos_comprador':bought,'pedidos_proveedor':sold,
        'moneda_catalogo_id':getattr(settings,'MARKETPLACE_CURRENCY_ID',1),
        'estadisticas':{'total_productos':len(products),'total_sucursales':len(branches),
            'total_pedidos_comprador':len(bought),'total_pedidos_proveedor':len(sold),
            'total_comprado':sum(Decimal(x['totalneto']) for x in bought), 'total_vendido':sum(Decimal(x['totalneto']) for x in sold)}}


def tokens(principal):
    refresh=RefreshToken.for_user(principal)
    refresh['company_id']=principal.company_id
    refresh['auth_version']=principal.version
    refresh['identity_source']='mongo'
    return {'access':str(refresh.access_token),'refresh':str(refresh)}


class RegisterSerializer(serializers.Serializer):
    nombre_usuario=serializers.CharField(max_length=100)
    correo=serializers.EmailField(max_length=150)
    contrasena=serializers.CharField(min_length=8,max_length=128,trim_whitespace=False)
    rol=serializers.ChoiceField(choices=['restaurant','provider'])
    razon_social=serializers.CharField(max_length=150)
    ruc=serializers.CharField(max_length=50)
    telefono=serializers.CharField(max_length=50)
    direccion_fiscal=serializers.CharField(max_length=250,required=False,allow_blank=True)
    logo_url=serializers.URLField(required=False,allow_blank=True,allow_null=True)


class ProfileSerializer(serializers.Serializer):
    nombreusuario=serializers.CharField(max_length=100,required=False)
    correoelectronico=serializers.EmailField(max_length=150,required=False)
    telefono=serializers.CharField(max_length=50,required=False,allow_blank=True)


class CompanySerializer(serializers.Serializer):
    razonsocial=serializers.CharField(max_length=150,required=False)
    ruc=serializers.CharField(max_length=50,required=False)
    telefono=serializers.CharField(max_length=50,required=False,allow_blank=True)
    correoempresa=serializers.EmailField(max_length=150,required=False,allow_blank=True)
    direccionfiscal=serializers.CharField(max_length=250,required=False,allow_blank=True)
    logourl=serializers.URLField(required=False,allow_blank=True,allow_null=True)
    estado=serializers.BooleanField(required=False)


class AuthViewSet(viewsets.ViewSet):
    permission_classes=[IsAuthenticated]
    def login(self,request):
        object_body(request)
        username=request.data.get('username',''); password=request.data.get('password','')
        if not isinstance(username,str) or not isinstance(password,str) or not username or not password or len(username)>150 or len(password)>128:
            raise ValidationError('Completa usuario y contrasena.')
        principal=identity.authenticate_credentials(username.strip(),password)
        data=snapshot(principal); data['tokens']=tokens(principal)
        return Response(data)
    dump_all_data=login

    def register(self,request):
        object_body(request)
        form=RegisterSerializer(data=request.data); form.is_valid(raise_exception=True); data=form.validated_data
        for field,value in [('correo',data['correo']),('nombre_usuario',data['nombre_usuario']),('ruc',data['ruc'])]:
            if identity.users().find_one({field:identity.exact(value)}): raise ValidationError({field:'Ya esta registrado.'})
        identifier=uuid4().hex
        document={'_id':'uer_'+identifier,'usuario_id':'usr_'+identifier,'empresa_id':'emp_'+identifier,
            'nombre_usuario':data['nombre_usuario'],'correo':data['correo'].lower(),'password_hash':make_password(data['contrasena']),
            'razon_social':data['razon_social'],'ruc':data['ruc'],'telefono_empresa':data['telefono'],
            'direccion_fiscal':data.get('direccion_fiscal',''),'logo_url':data.get('logo_url',''),
            'tipo_empresa':'Proveedor' if data['rol']=='provider' else 'Restaurante',
            'nombre_rol':'Proveedor' if data['rol']=='provider' else 'Cliente','rol_id':2 if data['rol']=='provider' else 1,
            'estado_usuario':True,'estado_rol':True,'fecha_registro':timezone.now().isoformat(),'fecha_asignacion':timezone.now().isoformat()}
        identity.users().insert_one(document)
        return Response({'usuario':identity.user_data(identity.Principal(document))},status=201)

    def refresh_token(self,request):
        object_body(request)
        try: refresh=RefreshToken(request.data.get('refresh',''))
        except TokenError: raise AuthenticationFailed('Refresh token invalido o expirado.')
        if refresh.get('identity_source')!='mongo' or type(refresh.get('auth_version')) is not int: raise AuthenticationFailed('Inicia sesion de nuevo.')
        principal=identity.resolve(refresh.get('user_id'),refresh.get('company_id'),refresh.get('auth_version',0))
        return Response({'access':str(refresh.access_token)})
    def me(self,request): return Response(identity.user_data(request.user))
    def my_data(self,request): return Response(snapshot(request.user))

    def update_profile(self,request):
        object_body(request)
        if set(request.data)-{'nombreusuario','correoelectronico','telefono'}: raise ValidationError('Campos no permitidos.')
        form=ProfileSerializer(data=request.data); form.is_valid(raise_exception=True)
        mapping={'nombreusuario':'nombre_usuario','correoelectronico':'correo','telefono':'telefono_usuario'}
        changes={mapping[k]:v for k,v in form.validated_data.items()}
        for field in ('nombre_usuario','correo'):
            if field in changes and identity.users().find_one({field:identity.exact(changes[field]),'usuario_id':{'$ne':request.user.pk}}):
                raise ValidationError({field:'Ya esta registrado.'})
        if changes: identity.users().update_many({'usuario_id':request.user.pk},{'$set':changes})
        return Response(identity.user_data(identity.resolve(request.user.pk,request.user.company_id)))

    def change_password(self,request):
        object_body(request)
        old=request.data.get('old_password'); new=request.data.get('new_password')
        if not isinstance(old,str) or not isinstance(new,str) or not 8<=len(new)<=128 or len(old)>128 or not check_password(old,request.user.document['password_hash']):
            raise ValidationError('La contrasena actual no coincide.')
        try: validate_password(new)
        except DjangoValidationError as exc: raise ValidationError({'new_password':exc.messages})
        result=identity.users().update_many({'usuario_id':request.user.pk,'password_hash':request.user.document['password_hash']},{'$set':{'password_hash':make_password(new)},'$inc':{'auth_version':1}})
        if not result.matched_count: raise AuthenticationFailed('La credencial cambio; vuelve a iniciar sesion.')
        current=identity.resolve(request.user.pk,request.user.company_id)
        return Response({'detail':'Contrasena actualizada.','tokens':tokens(current)})


class CompanyViewSet(viewsets.ViewSet):
    def list(self,request):
        data=identity.company_data(request.user)
        return Response([data] if data else [])
    def retrieve(self,request,pk=None):
        if str(pk)!=request.user.company_id: raise NotFound()
        return Response(identity.company_data(request.user))
    def update(self,request,pk=None):
        object_body(request)
        self.retrieve(request,pk)
        mapping={'razonsocial':'razon_social','ruc':'ruc','telefono':'telefono_empresa','correoempresa':'correo_empresa',
            'direccionfiscal':'direccion_fiscal','logourl':'logo_url'}
        if set(request.data)-set(mapping)-{'estado'}: raise ValidationError('Campos no permitidos.')
        if request.data.get('estado',True) is not True: raise ValidationError('El estado de acceso no se cambia desde este formulario.')
        form=CompanySerializer(data=request.data); form.is_valid(raise_exception=True)
        changes={mapping[k]:v for k,v in form.validated_data.items() if k in mapping}
        if 'razon_social' in changes and not changes['razon_social']: raise ValidationError('La razon social es obligatoria.')
        if 'ruc' in changes and identity.users().find_one({'ruc':identity.exact(changes['ruc']),'empresa_id':{'$ne':pk}}): raise ValidationError('RUC registrado.')
        if changes: identity.users().update_many({'empresa_id':pk},{'$set':changes})
        return Response(identity.company_data(identity.resolve(request.user.pk,pk)))
    partial_update=update
    @action(detail=True,methods=['get'])
    def sucursales(self,request,pk=None):
        self.retrieve(request,pk)
        return Response(BranchSerializer(m.SqlSucursal.objects.filter(empresaid=pk),many=True).data)


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class=BranchSerializer
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False): return m.SqlSucursal.objects.none()
        return m.SqlSucursal.objects.filter(empresaid=identity.company(self.request).pk).select_related('municipioid').order_by('pk')
    def perform_create(self,serializer):
        serializer.save(empresaid=identity.company(self.request).pk,codigosucursal='S'+uuid4().hex[:12],fecharegistro=timezone.now())
    def perform_destroy(self,instance):
        instance.estado='Inactivo'; instance.save(update_fields=['estado'])


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class=ProductSerializer
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False): return m.SqlProducto.objects.none()
        return product_query().filter(empresaid=identity.company(self.request,provider=True).pk,eliminado=False).order_by('pk')
    @transaction.atomic
    def perform_create(self,serializer):
        owner=identity.company(self.request,provider=True)
        serializer.validated_data.pop('stock_disponible',None)
        stock=serializer.validated_data.pop('stock_inicial',0); branch=serializer.validated_data.pop('sucursal_id',None)
        if stock and not m.SqlSucursal.objects.filter(pk=branch,empresaid=owner.pk,estado__in=['Activo','Activa']).exists():
            raise ValidationError('Selecciona una sucursal propia activa para el stock inicial.')
        product=serializer.save(empresaid=owner.pk,eliminado=False,cantidadminimapedido=serializer.validated_data.get('cantidadminimapedido',1))
        if stock: m.SqlInventariobodega.objects.create(productoid=product,sucursalid_id=branch,stockdisponible=stock,stockminimo=0,ultimaactualizacion=timezone.now())
    @transaction.atomic
    def perform_update(self,serializer):
        serializer.validated_data.pop('stock_inicial',None)
        stock=serializer.validated_data.pop('stock_disponible',None)
        branch=serializer.validated_data.pop('sucursal_id',None)
        owner=identity.company(self.request,provider=True)
        if stock is not None and not m.SqlSucursal.objects.filter(pk=branch,empresaid=owner.pk,estado__in=['Activo','Activa']).exists():
            raise ValidationError('Selecciona una sucursal propia activa.')
        product=serializer.save()
        if stock is not None:
            records=m.SqlInventariobodega.objects.select_for_update().filter(productoid=product,sucursalid_id=branch)
            if records.count()>1: raise ValidationError('Hay registros de inventario duplicados en esa sucursal.')
            record=records.first()
            if record:
                record.stockdisponible=stock; record.ultimaactualizacion=timezone.now()
                record.save(update_fields=['stockdisponible','ultimaactualizacion'])
            else: m.SqlInventariobodega.objects.create(productoid=product,sucursalid_id=branch,stockdisponible=stock,stockminimo=0,ultimaactualizacion=timezone.now())
    def perform_destroy(self,instance):
        instance.eliminado=True; instance.save(update_fields=['eliminado'])


class MarketplaceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes=[AllowAny]; serializer_class=ProductSerializer
    def get_queryset(self):
        query=product_query().filter(eliminado=False,sqlinventariobodega__stockdisponible__gt=0,
            sqlinventariobodega__sucursalid__estado__in=['Activo','Activa']).distinct()
        for param,field in [('categoria','categoriaid_id'),('proveedor','empresaid')]:
            if self.request.query_params.get(param): query=query.filter(**{field:self.request.query_params[param]})
        if self.request.query_params.get('search'): query=query.filter(nombreproducto__icontains=self.request.query_params['search'])
        return query.order_by('pk')


class InventoryViewSet(viewsets.ModelViewSet):
    serializer_class=InventorySerializer
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False): return m.SqlInventariobodega.objects.none()
        owner=identity.company(self.request,provider=True)
        return m.SqlInventariobodega.objects.filter(sucursalid__empresaid=owner.pk,productoid__empresaid=owner.pk).select_related('productoid','sucursalid').order_by('pk')
    def validate_owner(self,serializer):
        owner=identity.company(self.request,provider=True)
        product=serializer.validated_data.get('productoid',getattr(serializer.instance,'productoid',None))
        branch=serializer.validated_data.get('sucursalid',getattr(serializer.instance,'sucursalid',None))
        if not product or not branch or product.empresaid!=owner.pk or branch.empresaid!=owner.pk:
            raise ValidationError('Producto y sucursal deben pertenecer a tu empresa.')
        if m.SqlInventariobodega.objects.filter(productoid=product,sucursalid=branch).exclude(pk=getattr(serializer.instance,'pk',None)).exists():
            raise ValidationError('Ya existe stock para ese producto y sucursal.')
    def perform_create(self,serializer): self.validate_owner(serializer); serializer.save(ultimaactualizacion=timezone.now())
    def perform_update(self,serializer): self.validate_owner(serializer); serializer.save(ultimaactualizacion=timezone.now())


class PromotionViewSet(viewsets.ModelViewSet):
    serializer_class=model_serializer(m.SqlPromocion)
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False): return m.SqlPromocion.objects.none()
        return m.SqlPromocion.objects.filter(productoid__empresaid=identity.company(self.request,provider=True).pk).order_by('pk')
    def perform_create(self,serializer):
        product=serializer.validated_data.get('productoid',getattr(serializer.instance,'productoid',None))
        if not product or product.empresaid!=identity.company(self.request,provider=True).pk: raise PermissionDenied()
        percent=serializer.validated_data.get('porcentajedescuento',getattr(serializer.instance,'porcentajedescuento',0))
        if not 0<=percent<=100: raise ValidationError('Descuento invalido.')
        start=serializer.validated_data.get('fechainicio',getattr(serializer.instance,'fechainicio',None)); end=serializer.validated_data.get('fechafin',getattr(serializer.instance,'fechafin',None))
        if start and end and start>end: raise ValidationError('El periodo de la promocion es invalido.')
        serializer.save()
    def perform_update(self,serializer): self.perform_create(serializer)


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=OrderSerializer
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False): return m.SqlPedido.objects.none()
        owner=identity.company(self.request)
        return order_query().filter(Q(restauranteid=owner.pk)|Q(proveedorid=owner.pk))
    def create(self,request):
        order=create_order(request)
        return Response(self.get_serializer(order).data,status=201)
    @action(detail=False,methods=['post'])
    def cotizar(self,request): return Response(quote_order(request))
    @action(detail=True,methods=['put'])
    def update_status(self,request,pk=None):
        object_body(request)
        owner=identity.company(request,provider=True)
        with transaction.atomic():
            order=m.SqlPedido.objects.select_for_update().filter(pk=pk,proveedorid=owner.pk).first()
            if order is None: raise NotFound()
            try: state_id=int(request.data.get('estado_id'))
            except (TypeError,ValueError): raise ValidationError('Selecciona un estado valido.')
            state=m.SqlEstadopedido.objects.filter(pk=state_id).first()
            if state is None: raise ValidationError('Estado inexistente.')
            previous=order.estadopedidoid
            previous_name=previous.estadonombre.casefold(); next_name=state.estadonombre.casefold()
            terminal=('cancelado','cancelada','completado','entregado')
            if previous.pk!=state.pk and (previous_name in terminal or state.orden<previous.orden):
                raise ValidationError('La transicion de estado no esta permitida.')
            if next_name in ('cancelado','cancelada') and previous_name not in ('cancelado','cancelada'):
                for line in order.sqldetallepedido_set.order_by('productoid_id'):
                    records=m.SqlInventariobodega.objects.select_for_update().filter(productoid_id=line.productoid_id,sucursalid_id=order.sucursaloriginalid_id)
                    if records.count()!=1: raise ValidationError('No se puede devolver stock: el inventario de origen no es unico.')
                    record=records.first(); record.stockdisponible+=line.cantidad; record.ultimaactualizacion=timezone.now()
                    record.save(update_fields=['stockdisponible','ultimaactualizacion'])
            order.estadopedidoid=state; order.save(update_fields=['estadopedidoid'])
        return Response(OrderSerializer(order).data)


class DetailViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class=DetailSerializer
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False): return m.SqlDetallepedido.objects.none()
        owner=identity.company(self.request)
        return m.SqlDetallepedido.objects.filter(Q(pedidoid__restauranteid=owner.pk)|Q(pedidoid__proveedorid=owner.pk)).select_related('productoid').order_by('pk')


class DocumentsViewSet(viewsets.ModelViewSet):
    serializer_class=model_serializer(m.SqlDocumentosucursal)
    def get_queryset(self):
        if getattr(self,'swagger_fake_view',False): return m.SqlDocumentosucursal.objects.none()
        return m.SqlDocumentosucursal.objects.filter(sucursalid__empresaid=identity.company(self.request).pk).order_by('pk')
    def perform_create(self,serializer):
        branch=serializer.validated_data['sucursalid']
        if branch.empresaid!=identity.company(self.request).pk: raise PermissionDenied()
        serializer.save()
    def perform_update(self,serializer): self.perform_create(serializer)


def catalog_view(model):
    return type(model.__name__+'ViewSet',(viewsets.ReadOnlyModelViewSet,),{
        'permission_classes':[AllowAny], 'queryset':model.objects.order_by('pk'), 'serializer_class':model_serializer(model)})


class DashboardViewSet(viewsets.ViewSet):
    @action(detail=False,methods=['get'])
    def summary(self,request):
        from Tradconnect_no_sql.analytics_views import ProviderAnalyticsView
        data=ProviderAnalyticsView().get(request).data
        rows=data['ventas']
        total=sum(row['total_ventas'] for row in rows)
        count=sum(row['total_pedidos'] for row in rows)
        return Response({'total_ventas':total,'total_pedidos':count,'ticket_promedio':total/count if count else 0,
            'moneda_id':data['moneda'],'feedback':data['feedback']})
    @action(detail=False,methods=['get'])
    def sales_chart(self,request):
        from Tradconnect_no_sql.analytics_views import ProviderAnalyticsView
        return Response(ProviderAnalyticsView().get(request).data['ventas'])
    @action(detail=False,methods=['get'])
    def recent_orders(self,request):
        owner=identity.company(request,provider=True)
        return Response(OrderSerializer(order_query().filter(proveedorid=owner.pk)[:5],many=True).data)
