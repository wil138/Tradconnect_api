# views.py - TradConnect con Swagger, sin catálogos expuestos, sin Factura

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.db.models import Q, Sum
from django.utils import timezone
from django.db import transaction
from django.db.models.functions import TruncMonth
from django.contrib.auth.hashers import make_password, check_password
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    Usuario, Empresa, Rol, Producto, Sucursal, Pedido, Detallepedido,
    Inventariobodega, Historialestadopedido, Documentosucursal,
    Promocion, Estadopedido, Moneda, Metodopago, Unidadmedida, Categoria,
    Municipio, Departamento, Tipodocumento
)
from .serializers import (
    UsuarioSerializer, EmpresaSerializer, SucursalSerializer,
    ProductoSerializer, PedidoSerializer, DetallePedidoSerializer,
    HistorialEstadoPedidoSerializer, DocumentoSucursalSerializer,
    PromocionSerializer, InventarioBodegaSerializer,
    EmpresaRegistroSerializer, CategoriaSerializer, UnidadMedidaSerializer,
    MonedaSerializer, MetodoPagoSerializer, EstadoPedidoSerializer,
    DepartamentoSerializer, MunicipioSerializer, TipoDocumentoSerializer
)

# CORRECCIÓN: instanciar JWTAuthentication()
DEFAULT_AUTH = [JWTAuthentication]
DEFAULT_PERMS = [IsAuthenticated]

# =========================================================
# AUTENTICACIÓN (público) con Swagger
# =========================================================
class AuthViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="Registro de nuevo usuario y empresa",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['nombre_usuario', 'correo', 'contrasena', 'razon_social', 'ruc', 'telefono', 'rol'],
            properties={
                'nombre_usuario': openapi.Schema(type=openapi.TYPE_STRING),
                'correo': openapi.Schema(type=openapi.TYPE_STRING, format='email'),
                'contrasena': openapi.Schema(type=openapi.TYPE_STRING, format='password'),
                'razon_social': openapi.Schema(type=openapi.TYPE_STRING),
                'ruc': openapi.Schema(type=openapi.TYPE_STRING),
                'telefono': openapi.Schema(type=openapi.TYPE_STRING),
                'rol': openapi.Schema(type=openapi.TYPE_STRING, enum=['restaurant', 'provider']),
                'direccion_fiscal': openapi.Schema(type=openapi.TYPE_STRING),
                'logo_url': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={201: 'Creado', 400: 'Datos inválidos'},
        tags=['Autenticación']
    )
    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = EmpresaRegistroSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        v_data = serializer.validated_data
        rol_nombre = 'Restaurante' if v_data['rol'] == 'restaurant' else 'Proveedor'
        rol_obj = Rol.objects.get(nombrerol=rol_nombre)
        usuario = Usuario.objects.create(
            rolid=rol_obj,
            nombreusuario=v_data['nombre_usuario'],
            correoelectronico=v_data['correo'],
            contrasena=make_password(v_data['contrasena']),
            fecharegistro=timezone.now()
        )
        empresa = Empresa.objects.create(
            usuarioid=usuario, rolid=rol_obj,
            razonsocial=v_data['razon_social'], ruc=v_data['ruc'],
            telefono=v_data['telefono'], correoempresa=v_data['correo'],
            direccionfiscal=v_data.get('direccion_fiscal', ''),
            estado=True, logourl=v_data.get('logo_url', '')
        )
        refresh = RefreshToken.for_user(usuario)
        return Response({
            'refresh': str(refresh), 'access': str(refresh.access_token),
            'usuario': UsuarioSerializer(usuario).data,
            'empresa': EmpresaSerializer(empresa).data
        }, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_description="Inicio de sesión",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING, description="Email o nombre de usuario"),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format='password'),
            }
        ),
        responses={200: 'OK', 401: 'Credenciales inválidas'},
        tags=['Autenticación']
    )
    @action(detail=False, methods=['post'])
    def login(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        if not username or not password:
            return Response({'error': 'Usuario y contraseña obligatorios'}, status=400)
        usuario = Usuario.objects.filter(Q(correoelectronico__iexact=username) | Q(nombreusuario__iexact=username)).first()
        if not usuario:
            return Response({'error': 'Credenciales inválidas'}, status=401)
        valida = check_password(password, usuario.contrasena)
        if not valida:
            return Response({'error': 'Credenciales inválidas'}, status=401)
        empresa = Empresa.objects.filter(usuarioid=usuario).first()
        refresh = RefreshToken.for_user(usuario)
        return Response({
            'refresh': str(refresh), 'access': str(refresh.access_token),
            'usuario': UsuarioSerializer(usuario).data,
            'empresa': EmpresaSerializer(empresa).data if empresa else None
        })

    @swagger_auto_schema(
        operation_description="Refrescar token de acceso",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={'refresh': openapi.Schema(type=openapi.TYPE_STRING)}
        ),
        responses={200: 'OK', 401: 'Token inválido'},
        tags=['Autenticación']
    )
    @action(detail=False, methods=['post'])
    def refresh_token(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token requerido'}, status=400)
        try:
            refresh = RefreshToken(refresh_token)
            return Response({'access': str(refresh.access_token)})
        except Exception:
            return Response({'error': 'Token inválido'}, status=401)

    @swagger_auto_schema(
        operation_description="Obtener perfil del usuario autenticado",
        manual_parameters=[openapi.Parameter('Authorization', openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True)],
        responses={200: 'OK', 401: 'No autenticado'},
        tags=['Perfil']
    )
    @action(detail=False, methods=['get'], authentication_classes=DEFAULT_AUTH, permission_classes=DEFAULT_PERMS)
    def me(self, request):
        # 🔐 Solución robusta: extraer usuario manualmente del token
        # Esto evita problemas con el modelo de usuario personalizado
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Token no proporcionado o formato inválido'}, status=401)
        token = auth_header.split(' ')[1]
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            usuario = Usuario.objects.get(id=user_id)
        except Exception as e:
            return Response({'error': f'Token inválido: {str(e)}'}, status=401)

        empresa = Empresa.objects.filter(usuarioid=usuario).first()
        return Response({
            'usuario': UsuarioSerializer(usuario).data,
            'empresa': EmpresaSerializer(empresa).data if empresa else None
        })

    @swagger_auto_schema(
        operation_description="Datos básicos del usuario (empresa, sucursales, productos, pedidos recientes)",
        manual_parameters=[openapi.Parameter('Authorization', openapi.IN_HEADER, type=openapi.TYPE_STRING, required=True)],
        responses={200: 'OK', 401: 'No autenticado'},
        tags=['Perfil']
    )
    @action(detail=False, methods=['get'], authentication_classes=DEFAULT_AUTH, permission_classes=DEFAULT_PERMS)
    def my_data(self, request):
        # Extraer usuario manualmente también (por consistencia)
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return Response({'error': 'Token no proporcionado'}, status=401)
        token = auth_header.split(' ')[1]
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            usuario = Usuario.objects.get(id=user_id)
        except Exception:
            return Response({'error': 'Token inválido'}, status=401)

        empresa = Empresa.objects.filter(usuarioid=usuario).first()
        if not empresa:
            return Response({'error': 'Usuario sin empresa'}, status=400)
        sucursales = SucursalSerializer(Sucursal.objects.filter(empresaid=empresa), many=True).data
        productos = ProductoSerializer(Producto.objects.filter(empresaid=empresa, eliminado=False), many=True).data
        pedidos_comprador = PedidoSerializer(Pedido.objects.filter(restauranteid=empresa).order_by('-fechapedido')[:20], many=True).data
        pedidos_proveedor = PedidoSerializer(Pedido.objects.filter(proveedorid=empresa).order_by('-fechapedido')[:20], many=True).data
        inventario = InventarioBodegaSerializer(Inventariobodega.objects.filter(sucursalid__empresaid=empresa), many=True).data
        promociones = PromocionSerializer(Promocion.objects.filter(productoid__empresaid=empresa), many=True).data
        documentos = DocumentoSucursalSerializer(Documentosucursal.objects.filter(sucursalid__empresaid=empresa), many=True).data
        stats = {
            'total_productos': len(productos),
            'total_sucursales': len(sucursales),
            'total_pedidos_comprador': len(pedidos_comprador),
            'total_pedidos_proveedor': len(pedidos_proveedor),
        }
        return Response({
            'usuario': UsuarioSerializer(usuario).data,
            'empresa': EmpresaSerializer(empresa).data,
            'sucursales': sucursales,
            'productos': productos,
            'pedidos_comprador': pedidos_comprador,
            'pedidos_proveedor': pedidos_proveedor,
            'inventario': inventario,
            'promociones': promociones,
            'documentos': documentos,
            'estadisticas': stats
        })

    @swagger_auto_schema(
        operation_description="Volcado completo de datos (tipo NoSQL) incluyendo catálogos",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format='password'),
            }
        ),
        responses={200: 'OK', 401: 'Credenciales inválidas'},
        tags=['Autenticación']
    )
    @action(detail=False, methods=['post'])
    def dump_all_data(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        if not username or not password:
            return Response({'error': 'Usuario y contraseña obligatorios'}, status=400)
        usuario = Usuario.objects.filter(Q(correoelectronico__iexact=username) | Q(nombreusuario__iexact=username)).first()
        if not usuario:
            return Response({'error': 'Usuario no encontrado'}, status=401)
        valida = check_password(password, usuario.contrasena)
        if not valida:
            return Response({'error': 'Contraseña incorrecta'}, status=401)

        empresa = Empresa.objects.filter(usuarioid=usuario).first()
        refresh = RefreshToken.for_user(usuario)

        def serialize_qs(qs, serializer_class):
            return serializer_class(qs, many=True).data

        dump = {
            'tokens': {'access': str(refresh.access_token), 'refresh': str(refresh)},
            'usuario': UsuarioSerializer(usuario).data,
            'empresa': EmpresaSerializer(empresa).data if empresa else None,
            'catalogos': {
                'categorias': serialize_qs(Categoria.objects.all(), CategoriaSerializer),
                'unidades_medida': serialize_qs(Unidadmedida.objects.all(), UnidadMedidaSerializer),
                'metodos_pago': serialize_qs(Metodopago.objects.all(), MetodoPagoSerializer),
                'monedas': serialize_qs(Moneda.objects.all(), MonedaSerializer),
                'estados_pedido': serialize_qs(Estadopedido.objects.all(), EstadoPedidoSerializer),
                'departamentos': serialize_qs(Departamento.objects.all(), DepartamentoSerializer),
                'municipios': serialize_qs(Municipio.objects.all(), MunicipioSerializer),
                'tipos_documento': serialize_qs(Tipodocumento.objects.all(), TipoDocumentoSerializer),
            }
        }
        if empresa:
            dump['sucursales'] = serialize_qs(Sucursal.objects.filter(empresaid=empresa), SucursalSerializer)
            dump['productos'] = serialize_qs(Producto.objects.filter(empresaid=empresa, eliminado=False), ProductoSerializer)
            dump['pedidos_comprador'] = serialize_qs(Pedido.objects.filter(restauranteid=empresa).order_by('-fechapedido'), PedidoSerializer)
            dump['pedidos_proveedor'] = serialize_qs(Pedido.objects.filter(proveedorid=empresa).order_by('-fechapedido'), PedidoSerializer)
            dump['inventario'] = serialize_qs(Inventariobodega.objects.filter(sucursalid__empresaid=empresa), InventarioBodegaSerializer)
            dump['promociones'] = serialize_qs(Promocion.objects.filter(productoid__empresaid=empresa), PromocionSerializer)
            total_comprado = Pedido.objects.filter(restauranteid=empresa).aggregate(total=Sum('totalneto'))['total'] or 0
            total_vendido = Pedido.objects.filter(proveedorid=empresa).aggregate(total=Sum('totalneto'))['total'] or 0
            dump['estadisticas'] = {
                'total_productos': len(dump['productos']),
                'total_sucursales': len(dump['sucursales']),
                'total_pedidos_comprador': len(dump['pedidos_comprador']),
                'total_pedidos_proveedor': len(dump['pedidos_proveedor']),
                'total_comprado': float(total_comprado),
                'total_vendido': float(total_vendido),
            }
        return Response(dump)

# =========================================================
# MARKETPLACE (público, solo lectura)
# =========================================================
class MarketplaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Producto.objects.filter(eliminado=False)
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Marketplace'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# EMPRESAS (privado)
# =========================================================
class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    @swagger_auto_schema(tags=['Empresas'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# SUCURSALES (privado)
# =========================================================
class SucursalViewSet(viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    @swagger_auto_schema(tags=['Sucursales'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# PRODUCTOS (solo del usuario autenticado) - CON PROTECCIÓN SWAGGER
# =========================================================
class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    def get_queryset(self):
        # 🔴 Protección contra peticiones falsas de Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Producto.objects.none()
        # 🔴 Protección contra usuario anónimo
        if not self.request.user or self.request.user.is_anonymous:
            return Producto.objects.none()
        empresa = Empresa.objects.filter(usuarioid=self.request.user).first()
        if not empresa:
            return Producto.objects.none()
        return Producto.objects.filter(empresaid=empresa, eliminado=False)

    def perform_create(self, serializer):
        empresa = Empresa.objects.filter(usuarioid=self.request.user).first()
        serializer.save(empresaid=empresa)

    @swagger_auto_schema(tags=['Productos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# INVENTARIO POR BODEGA (privado) - CON PROTECCIÓN SWAGGER
# =========================================================
class InventarioBodegaViewSet(viewsets.ModelViewSet):
    serializer_class = InventarioBodegaSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Inventariobodega.objects.none()
        if not self.request.user or self.request.user.is_anonymous:
            return Inventariobodega.objects.none()
        empresa = Empresa.objects.filter(usuarioid=self.request.user).first()
        if not empresa:
            return Inventariobodega.objects.none()
        return Inventariobodega.objects.filter(sucursalid__empresaid=empresa)

    @swagger_auto_schema(tags=['Inventario'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# PROMOCIONES (privado) - CON PROTECCIÓN SWAGGER
# =========================================================
class PromocionViewSet(viewsets.ModelViewSet):
    serializer_class = PromocionSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Promocion.objects.none()
        if not self.request.user or self.request.user.is_anonymous:
            return Promocion.objects.none()
        empresa = Empresa.objects.filter(usuarioid=self.request.user).first()
        if not empresa:
            return Promocion.objects.none()
        return Promocion.objects.filter(productoid__empresaid=empresa)

    @swagger_auto_schema(tags=['Promociones'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# PEDIDOS (privado) + cambio de estado - CON PROTECCIÓN SWAGGER
# =========================================================
class PedidoViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Pedido.objects.none()
        if not self.request.user or self.request.user.is_anonymous:
            return Pedido.objects.none()
        user = self.request.user
        empresa = Empresa.objects.filter(usuarioid=user).first()
        if not empresa:
            return Pedido.objects.none()
        if empresa.rolid.nombrerol == 'Restaurante':
            return Pedido.objects.filter(restauranteid=empresa)
        else:
            return Pedido.objects.filter(proveedorid=empresa)

    @swagger_auto_schema(
        operation_description="Crear un nuevo pedido (solo restaurantes)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['proveedor_id', 'sucursal_origen_id', 'sucursal_entrega_id', 'metodo_pago_id', 'items'],
            properties={
                'proveedor_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'sucursal_origen_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'sucursal_entrega_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'metodo_pago_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'moneda_id': openapi.Schema(type=openapi.TYPE_INTEGER, default=1),
                'comentario': openapi.Schema(type=openapi.TYPE_STRING),
                'items': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'producto_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'cantidad': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'precio_unitario': openapi.Schema(type=openapi.TYPE_NUMBER),
                            'descuento': openapi.Schema(type=openapi.TYPE_NUMBER),
                        }
                    )
                )
            }
        ),
        responses={201: 'Pedido creado', 403: 'No autorizado'},
        tags=['Pedidos']
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        restaurante = Empresa.objects.filter(usuarioid=user, rolid__nombrerol='Restaurante').first()
        if not restaurante:
            return Response({'error': 'Solo restaurantes pueden crear pedidos'}, status=403)
        proveedor = Empresa.objects.get(id=data['proveedor_id'])
        sucursal_origen = Sucursal.objects.get(id=data['sucursal_origen_id'])
        sucursal_entrega = Sucursal.objects.get(id=data['sucursal_entrega_id'])
        moneda = Moneda.objects.get(id=data.get('moneda_id', 1))
        metodo_pago = Metodopago.objects.get(id=data['metodo_pago_id'])

        subtotal = 0
        items_data = data['items']
        for item in items_data:
            precio = item['precio_unitario']
            cantidad = item['cantidad']
            subtotal += precio * cantidad
        impuesto = subtotal * 0.15
        total = subtotal + impuesto

        pedido = Pedido.objects.create(
            restauranteid=restaurante,
            proveedorid=proveedor,
            sucursalorigenid=sucursal_origen,
            sucursalentregaid=sucursal_entrega,
            monedaid=moneda,
            metodopagoid=metodo_pago,
            subtotal=subtotal,
            impuesto=impuesto,
            totalneto=total,
            comentario=data.get('comentario', ''),
            fechapedido=timezone.now()
        )
        for item in items_data:
            producto = Producto.objects.get(id=item['producto_id'])
            Detallepedido.objects.create(
                pedidoid=pedido,
                productoid=producto,
                cantidad=item['cantidad'],
                preciounitario=item['precio_unitario'],
                descuentoaplicado=item.get('descuento', 0)
            )
        estado_pendiente = Estadopedido.objects.get(estadonombre__iexact='Pendiente')
        Historialestadopedido.objects.create(
            pedidoid=pedido,
            estadoid=estado_pendiente,
            comentario='Pedido creado',
            fechacambio=timezone.now()
        )
        return Response(PedidoSerializer(pedido).data, status=201)

    @swagger_auto_schema(
        operation_description="Cambiar estado de un pedido (solo proveedor)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['estado_id'],
            properties={
                'estado_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'comentario': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={200: 'OK', 403: 'No autorizado', 400: 'Stock insuficiente'},
        tags=['Pedidos']
    )
    @action(detail=True, methods=['put'])
    @transaction.atomic
    def update_status(self, request, pk=None):
        pedido = self.get_object()
        user = request.user
        empresa = Empresa.objects.filter(usuarioid=user).first()
        if not empresa or pedido.proveedorid != empresa:
            return Response({'error': 'No autorizado'}, status=403)
        nuevo_estado_id = request.data.get('estado_id')
        comentario = request.data.get('comentario', '')
        try:
            nuevo_estado = Estadopedido.objects.get(id=nuevo_estado_id)
        except Estadopedido.DoesNotExist:
            return Response({'error': 'Estado inválido'}, status=400)

        Historialestadopedido.objects.create(
            pedidoid=pedido,
            estadoid=nuevo_estado,
            comentario=comentario,
            fechacambio=timezone.now()
        )
        # Descontar stock si nuevo estado es "Completado"
        if nuevo_estado.estadonombre.lower() == 'completado':
            detalles = Detallepedido.objects.filter(pedidoid=pedido)
            for detalle in detalles:
                inventario = Inventariobodega.objects.filter(
                    productoid=detalle.productoid,
                    sucursalid=pedido.sucursalorigenid
                ).first()
                if inventario:
                    if inventario.stockdisponible >= detalle.cantidad:
                        inventario.stockdisponible -= detalle.cantidad
                        inventario.ultimaactualizacion = timezone.now()
                        inventario.save()
                    else:
                        return Response({'error': f'Stock insuficiente para {detalle.productoid.nombreproducto}'}, status=400)
        return Response({'success': True, 'nuevo_estado': nuevo_estado.estadonombre})

    @swagger_auto_schema(tags=['Pedidos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# DETALLES DE PEDIDO, HISTORIAL, DOCUMENTOS - CON PROTECCIÓN SWAGGER
# =========================================================
class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = Detallepedido.objects.all()
    serializer_class = DetallePedidoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Detallepedido.objects.none()
        return super().get_queryset()
    
    @swagger_auto_schema(tags=['Detalles de Pedido'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class HistorialEstadoPedidoViewSet(viewsets.ModelViewSet):
    queryset = Historialestadopedido.objects.all()
    serializer_class = HistorialEstadoPedidoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Historialestadopedido.objects.none()
        return super().get_queryset()
    
    @swagger_auto_schema(tags=['Historial de Estados'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

class DocumentoSucursalViewSet(viewsets.ModelViewSet):
    queryset = Documentosucursal.objects.all()
    serializer_class = DocumentoSucursalSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Documentosucursal.objects.none()
        return super().get_queryset()
    
    @swagger_auto_schema(tags=['Documentos de Sucursal'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

# =========================================================
# DASHBOARD PARA PROVEEDORES - CON PROTECCIÓN SWAGGER
# =========================================================
class ProviderDashboardViewSet(viewsets.ViewSet):
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    def _check_swagger(self, request):
        return getattr(self, 'swagger_fake_view', False) or not request.user or request.user.is_anonymous

    @swagger_auto_schema(
        operation_description="Resumen de ventas, pedidos y productos con stock bajo",
        responses={200: 'OK', 403: 'No eres proveedor'},
        tags=['Dashboard']
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        if self._check_swagger(request):
            return Response({})
        empresa = Empresa.objects.filter(usuarioid=request.user, rolid__nombrerol='Proveedor').first()
        if not empresa:
            return Response({'error': 'No eres proveedor'}, status=403)
        pedidos = Pedido.objects.filter(proveedorid=empresa)
        total_ventas = pedidos.aggregate(total=Sum('totalneto'))['total'] or 0
        sucursales = Sucursal.objects.filter(empresaid=empresa)
        low_stock = Inventariobodega.objects.filter(sucursalid__in=sucursales, stockdisponible__lte=10).count()
        return Response({
            'total_ventas': float(total_ventas),
            'total_pedidos': pedidos.count(),
            'productos_stock_bajo': low_stock
        })

    @swagger_auto_schema(
        operation_description="Pedidos recientes (últimos N)",
        manual_parameters=[
            openapi.Parameter('limite', openapi.IN_QUERY, type=openapi.TYPE_INTEGER, description='Número de pedidos a devolver')
        ],
        responses={200: 'OK', 403: 'No eres proveedor'},
        tags=['Dashboard']
    )
    @action(detail=False, methods=['get'])
    def recent_orders(self, request):
        if self._check_swagger(request):
            return Response([])
        empresa = Empresa.objects.filter(usuarioid=request.user, rolid__nombrerol='Proveedor').first()
        if not empresa:
            return Response({'error': 'No eres proveedor'}, status=403)
        limite = int(request.query_params.get('limite', 10))
        pedidos = Pedido.objects.filter(proveedorid=empresa).order_by('-fechapedido')[:limite]
        return Response(PedidoSerializer(pedidos, many=True).data)

    @swagger_auto_schema(
        operation_description="Ventas mensuales para gráfico de líneas",
        responses={200: 'OK', 403: 'No eres proveedor'},
        tags=['Dashboard']
    )
    @action(detail=False, methods=['get'])
    def sales_chart(self, request):
        if self._check_swagger(request):
            return Response({'labels': [], 'data': []})
        empresa = Empresa.objects.filter(usuarioid=request.user, rolid__nombrerol='Proveedor').first()
        if not empresa:
            return Response({'error': 'No eres proveedor'}, status=403)
        ventas_mensuales = (Pedido.objects
            .filter(proveedorid=empresa, fechapedido__isnull=False)
            .annotate(mes=TruncMonth('fechapedido'))
            .values('mes').annotate(total=Sum('totalneto')).order_by('mes'))
        labels = [v['mes'].strftime('%b %Y') for v in ventas_mensuales]
        data = [float(v['total']) for v in ventas_mensuales]
        return Response({'labels': labels, 'data': data})


# =========================================================
# CATÁLOGOS PÚBLICOS (solo lectura, sin autenticación)
# =========================================================

class CategoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lista de categorías de productos.
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class UnidadMedidaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Unidadmedida.objects.all()
    serializer_class = UnidadMedidaSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class MonedaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Moneda.objects.all()
    serializer_class = MonedaSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class MetodoPagoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Metodopago.objects.all()
    serializer_class = MetodoPagoSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class EstadoPedidoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Estadopedido.objects.all()
    serializer_class = EstadoPedidoSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class DepartamentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class MunicipioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Municipio.objects.all()
    serializer_class = MunicipioSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TipoDocumentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tipodocumento.objects.all()
    serializer_class = TipoDocumentoSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=['Catálogos Públicos'])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)