# views.py - Desarrollado para TradConnect con soporte de AuthJWT Híbrido
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q, Sum
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.functions import TruncMonth

from .models import (
    Usuario, Empresa, Rol, Producto, Categoria, Sucursal, Municipio,
    Departamento, Pedido, Detallepedido, Factura, Promocion,
    Unidadmedida, Moneda, Metodopago, Estadopedido, Inventariobodega,
    Historialestadopedido, Documentosucursal, Tipodocumento
)

from .serializers import (
    CategoriaSerializer, EstadoPedidoSerializer, MetodoPagoSerializer,
    MonedaSerializer, UnidadMedidaSerializer, RolSerializer, DepartamentoSerializer,
    MunicipioSerializer, TipoDocumentoSerializer,
    UsuarioSerializer, EmpresaSerializer, EmpresaRegistroSerializer,
    SucursalSerializer, ProductoSerializer, PedidoSerializer,
    DetallePedidoSerializer, FacturaSerializer, PromocionSerializer,
    InventarioBodegaSerializer, HistorialEstadoPedidoSerializer, DocumentoSucursalSerializer
)

DEFAULT_AUTH = [JWTAuthentication()]
DEFAULT_PERMS = [IsAuthenticated]

# =========================================================
# CONTROLADOR DE AUTENTICACIÓN (LOGIN Y REGISTRO)
# =========================================================
class AuthViewSet(viewsets.ViewSet):
    authentication_classes = []
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = EmpresaRegistroSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        v_data = serializer.validated_data
        
        # Obtener el Rol correspondiente en la BD de SQL Server
        nombre_rol_bd = 'Restaurante' if v_data['rol'] == 'restaurant' else 'Proveedor'
        rol_obj = Rol.objects.filter(nombrerol=nombre_rol_bd).first()
        if not rol_obj:
            return Response({'error': f'El Rol {nombre_rol_bd} no está inicializado en la BD.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        # 1. Crear el Registro de Usuario
        nuevo_usuario = Usuario.objects.create(
            rolid=rol_obj,
            nombreusuario=v_data['nombre_usuario'],
            correoelectronico=v_data['correo'],
            contrasena=make_password(v_data['contrasena']),
            fecharegistro=timezone.now()
        )
        
        # 2. Crear la Empresa enlazada
        nueva_empresa = Empresa.objects.create(
            usuarioid=nuevo_usuario,
            rolid=rol_obj,
            razonsocial=v_data['razon_social'],
            ruc=v_data['ruc'],
            telefono=v_data['telefono'],
            correoempresa=v_data['correo'],
            direccionfiscal=v_data.get('direccion_fiscal', ''),
            estado=1,
            logourl=v_data.get('logo_url', '')
        )
        
        # Generar Tokens JWT de respuesta inmediata
        refresh = RefreshToken.for_user(nuevo_usuario)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'usuario': UsuarioSerializer(nuevo_usuario).data,
            'empresa': EmpresaSerializer(nueva_empresa).data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        identificador = request.data.get('identificador')
        contrasena = request.data.get('contrasena')

        if not identificador or not contrasena:
            return Response({'error': 'Los campos identificador y contrasena son obligatorios.'}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar usuario por nombre de usuario o correo electrónico
        usuario = Usuario.objects.filter(Q(correoelectronico=identificador) | Q(nombreusuario=identificador)).first()
        if not usuario:
            return Response({'error': 'Credenciales inválidas (Usuario no encontrado).'}, status=status.HTTP_401_UNAUTHORIZED)

        # Validación Híbrida: Soporta texto plano de los Mock Scripts y hashes seguros de Django
        es_valida = False
        if usuario.contrasena.startswith('pbkdf2_') or usuario.contrasena.startswith('bcrypt'):
            es_valida = check_password(contrasena, usuario.contrasena)
        else:
            es_valida = (contrasena == usuario.contrasena)

        if not es_valida:
            return Response({'error': 'Credenciales inválidas (Contraseña incorrecta).'}, status=status.HTTP_401_UNAUTHORIZED)

        # Obtener metadata de la empresa vinculada
        empresa = Empresa.objects.filter(usuarioid=usuario).first()
        empresa_data = EmpresaSerializer(empresa).data if empresa else None

        refresh = RefreshToken.for_user(usuario)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'usuario': UsuarioSerializer(usuario).data,
            'empresa': empresa_data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], authentication_classes=DEFAULT_AUTH, permission_classes=DEFAULT_PERMS)
    def me(self, request):
        usuario = request.user
        empresa = Empresa.objects.filter(usuarioid=usuario).first()
        return Response({
            'usuario': UsuarioSerializer(usuario).data,
            'empresa': EmpresaSerializer(empresa).data if empresa else None
        })

# =========================================================
# VIEWSETS DEL CORE DEL NEGOCIO (CRUD AUTOMÁTICO)
# =========================================================
class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [AllowAny]

class DepartamentoViewSet(viewsets.ModelViewSet):
    queryset = Departamento.objects.all()
    serializer_class = DepartamentoSerializer
    permission_classes = [AllowAny]

class MunicipioViewSet(viewsets.ModelViewSet):
    queryset = Municipio.objects.all()
    serializer_class = MunicipioSerializer
    permission_classes = [AllowAny]

class EstadoPedidoViewSet(viewsets.ModelViewSet):
    queryset = Estadopedido.objects.all()
    serializer_class = EstadoPedidoSerializer
    permission_classes = [AllowAny]

class MetodoPagoViewSet(viewsets.ModelViewSet):
    queryset = Metodopago.objects.all()
    serializer_class = MetodoPagoSerializer
    permission_classes = [AllowAny]

class MonedaViewSet(viewsets.ModelViewSet):
    queryset = Moneda.objects.all()
    serializer_class = MonedaSerializer
    permission_classes = [AllowAny]

class UnidadMedidaViewSet(viewsets.ModelViewSet):
    queryset = Unidadmedida.objects.all()
    serializer_class = UnidadMedidaSerializer
    permission_classes = [AllowAny]

class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all()
    serializer_class = RolSerializer
    permission_classes = [AllowAny]

class TipoDocumentoViewSet(viewsets.ModelViewSet):
    queryset = Tipodocumento.objects.all()
    serializer_class = TipoDocumentoSerializer
    permission_classes = [AllowAny]

class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class SucursalViewSet(viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.filter(eliminado=False)
    serializer_class = ProductoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class InventarioBodegaViewSet(viewsets.ModelViewSet):
    queryset = Inventariobodega.objects.all()
    serializer_class = InventarioBodegaSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class PromocionViewSet(viewsets.ModelViewSet):
    queryset = Promocion.objects.all()
    serializer_class = PromocionSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = Detallepedido.objects.all()
    serializer_class = DetallePedidoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class HistorialEstadoPedidoViewSet(viewsets.ModelViewSet):
    queryset = Historialestadopedido.objects.all()
    serializer_class = HistorialEstadoPedidoSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class DocumentoSucursalViewSet(viewsets.ModelViewSet):
    queryset = Documentosucursal.objects.all()
    serializer_class = DocumentoSucursalSerializer
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

class MarketplaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Producto.objects.filter(eliminado=False)
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]

class ProviderDashboardViewSet(viewsets.ViewSet):
    authentication_classes = DEFAULT_AUTH
    permission_classes = DEFAULT_PERMS

    @action(detail=False, methods=['get'])
    def summary(self, request):
        empresa = Empresa.objects.filter(usuarioid=request.user, rolid__nombrerol='Proveedor').first()
        if not empresa:
            return Response({'error': 'No eres un proveedor registrado.'}, status=status.HTTP_403_FORBIDDEN)
        
        pedidos = Pedido.objects.filter(proveedorid=empresa)
        total_ventas = pedidos.aggregate(Sum('totalneto'))['totalneto__sum'] or 0.0
        conteo_pedidos = pedidos.count()
        
        sucursales = Sucursal.objects.filter(empresaid=empresa)
        low_stock = Inventariobodega.objects.filter(sucursalid__in=sucursales, stockdisponible__lte=10).count()
        
        return Response({
            'total_sales': float(total_ventas),
            'total_orders': conteo_pedidos,
            'low_stock_items': low_stock
        })

    @action(detail=False, methods=['get'])
    def recent_orders(self, request):
        empresa = Empresa.objects.filter(usuarioid=request.user, rolid__nombrerol='Proveedor').first()
        if not empresa:
            return Response({'error': 'No eres un proveedor registrado.'}, status=status.HTTP_403_FORBIDDEN)
        pedidos = Pedido.objects.filter(proveedorid=empresa).order_by('-fechapedido')[:10]
        serializer = PedidoSerializer(pedidos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def sales_chart(self, request):
        empresa = Empresa.objects.filter(usuarioid=request.user, rolid__nombrerol='Proveedor').first()
        if not empresa:
            return Response({'error': 'No eres un proveedor registrado.'}, status=status.HTTP_403_FORBIDDEN)
        
        ventas_mensuales = (Pedido.objects
            .filter(proveedorid=empresa, fechapedido__isnull=False)
            .annotate(mes=TruncMonth('fechapedido'))
            .values('mes')
            .annotate(total=Sum('totalneto'))
            .order_by('mes'))
        
        labels = [v['mes'].strftime('%b %Y') for v in ventas_mensuales]
        data = [float(v['total']) for v in ventas_mensuales]
        
        return Response({'labels': labels, 'data': data})