# serializers.py - TradConnect (sin catálogos expuestos, sin Factura)

from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .models import (
    Usuario, Empresa, Rol, Producto, Categoria, Sucursal, Municipio,
    Departamento, Pedido, Detallepedido, Promocion, Unidadmedida,
    Moneda, Metodopago, Estadopedido, Inventariobodega,
    Historialestadopedido, Documentosucursal, Tipodocumento
)

# =========================================================
# CATÁLOGOS (serializers internos, NO se exponen como endpoints)
# =========================================================
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombrecategoria', 'descripcion', 'icono', 'colorhex']

class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidadmedida
        fields = ['id', 'nombreunidad', 'abreviatura', 'icono']

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ['id', 'nombremoneda', 'simbolo', 'icono']

class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metodopago
        fields = ['id', 'nombremetodo', 'icono', 'descripcion']

class EstadoPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estadopedido
        fields = ['id', 'estadonombre', 'icono', 'colorhex']

class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'nombredepartamento']

class MunicipioSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.CharField(source='departamentoid.nombredepartamento', read_only=True)
    class Meta:
        model = Municipio
        fields = ['id', 'nombremunicipio', 'departamentoid', 'departamento_nombre']

class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tipodocumento
        fields = ['id', 'nombredocumento', 'icono']

# =========================================================
# USUARIO Y EMPRESA
# =========================================================
class UsuarioSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rolid.nombrerol', read_only=True)
    class Meta:
        model = Usuario
        fields = ['id', 'rolid', 'rol_nombre', 'nombreusuario', 'correoelectronico', 'fecharegistro']

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ['id', 'usuarioid', 'rolid', 'razonsocial', 'ruc', 'telefono',
                  'correoempresa', 'direccionfiscal', 'estado', 'logourl']

class EmpresaRegistroSerializer(serializers.Serializer):
    nombre_usuario = serializers.CharField(max_length=100)
    correo = serializers.EmailField()
    contrasena = serializers.CharField(write_only=True)
    rol = serializers.ChoiceField(choices=[('restaurant', 'Restaurante'), ('provider', 'Proveedor')])
    razon_social = serializers.CharField(max_length=200)
    ruc = serializers.CharField(max_length=50)
    telefono = serializers.CharField(max_length=50)
    direccion_fiscal = serializers.CharField(required=False, allow_blank=True)
    logo_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    def validate_correo(self, value):
        if Usuario.objects.filter(correoelectronico=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

# =========================================================
# SUCURSALES
# =========================================================
class SucursalSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(source='municipioid.nombremunicipio', read_only=True)
    class Meta:
        model = Sucursal
        fields = ['id', 'empresaid', 'nombresucursal', 'municipioid', 'municipio_nombre',
                  'direccionexacta', 'telefonosucursal', 'horarioatencion', 'esbodega', 'estado']

# =========================================================
# PRODUCTOS (con stock actual desde InventarioBodega)
# =========================================================
class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoriaid.nombrecategoria', read_only=True)
    unidad_nombre = serializers.CharField(source='unidadmedidaid.nombreunidad', read_only=True)
    stock_disponible = serializers.SerializerMethodField()
    class Meta:
        model = Producto
        fields = ['id', 'empresaid', 'categoriaid', 'categoria_nombre',
                  'unidadmedidaid', 'unidad_nombre', 'nombreproducto', 'descripcion',
                  'precioventa', 'cantidadminimapedido', 'esperecedero', 'diasvidautil',
                  'imagenurl', 'eliminado', 'stock_disponible']

    def get_stock_disponible(self, obj):
        # Suma de stock en todas las sucursales de la empresa (para vista general)
        total = Inventariobodega.objects.filter(productoid=obj).aggregate(total=models.Sum('stockdisponible'))['total']
        return float(total) if total else 0.0

# =========================================================
# INVENTARIO POR BODEGA
# =========================================================
class InventarioBodegaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='productoid.nombreproducto', read_only=True)
    sucursal_nombre = serializers.CharField(source='sucursalid.nombresucursal', read_only=True)
    class Meta:
        model = Inventariobodega
        fields = ['id', 'productoid', 'producto_nombre', 'sucursalid', 'sucursal_nombre',
                  'stockdisponible', 'stockminimo', 'ultimaactualizacion']

# =========================================================
# PROMOCIONES
# =========================================================
class PromocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocion
        fields = ['id', 'productoid', 'descripcion', 'cantidadminima',
                  'porcentajedescuento', 'fechainicio', 'fechafin']

# =========================================================
# PEDIDOS (con estado actual desde historial, sin Factura)
# =========================================================
class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='productoid.nombreproducto', read_only=True)
    subtotal = serializers.SerializerMethodField()
    class Meta:
        model = Detallepedido
        fields = ['id', 'pedidoid', 'productoid', 'producto_nombre', 'cantidad',
                  'preciounitario', 'descuentoaplicado', 'subtotal']
    def get_subtotal(self, obj):
        precio = float(obj.preciounitario)
        cant = float(obj.cantidad)
        desc = float(obj.descuentoaplicado or 0)
        return precio * cant * (1 - desc/100)

class PedidoSerializer(serializers.ModelSerializer):
    restaurante_nombre = serializers.CharField(source='restauranteid.razonsocial', read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedorid.razonsocial', read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True, source='detallepedido_set')
    estado_actual = serializers.SerializerMethodField()
    estado_color = serializers.SerializerMethodField()
    estado_icono = serializers.SerializerMethodField()
    fecha_completado = serializers.SerializerMethodField()
    tiene_factura = serializers.SerializerMethodField()   # True si estado = "Completado"

    class Meta:
        model = Pedido
        fields = ['id', 'restauranteid', 'restaurante_nombre', 'proveedorid', 'proveedor_nombre',
                  'sucursalorigenid', 'sucursalentregaid', 'monedaid', 'metodopagoid',
                  'subtotal', 'impuesto', 'totalneto', 'comentario', 'fechapedido',
                  'detalles', 'estado_actual', 'estado_color', 'estado_icono',
                  'fecha_completado', 'tiene_factura']

    def get_estado_actual(self, obj):
        ultimo = obj.historialestadopedido_set.order_by('-fechacambio').first()
        return ultimo.estadoid.estadonombre if ultimo else 'Sin estado'

    def get_estado_color(self, obj):
        ultimo = obj.historialestadopedido_set.order_by('-fechacambio').first()
        return ultimo.estadoid.colorhex if ultimo else '#6c757d'

    def get_estado_icono(self, obj):
        ultimo = obj.historialestadopedido_set.order_by('-fechacambio').first()
        return ultimo.estadoid.icono if ultimo else 'fa-question'

    def get_fecha_completado(self, obj):
        completado = obj.historialestadopedido_set.filter(estadoid__estadonombre__iexact='Completado').order_by('-fechacambio').first()
        return completado.fechacambio if completado else None

    def get_tiene_factura(self, obj):
        return self.get_estado_actual(obj) == 'Completado'

# =========================================================
# HISTORIAL DE ESTADOS
# =========================================================
class HistorialEstadoPedidoSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source='estadoid.estadonombre', read_only=True)
    class Meta:
        model = Historialestadopedido
        fields = ['id', 'pedidoid', 'estadoid', 'estado_nombre', 'comentario', 'fechacambio']

# =========================================================
# DOCUMENTOS DE SUCURSAL
# =========================================================
class DocumentoSucursalSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(source='sucursalid.nombresucursal', read_only=True)
    tipo_documento_nombre = serializers.CharField(source='tipodocumentoid.nombredocumento', read_only=True)
    class Meta:
        model = Documentosucursal
        fields = ['id', 'sucursalid', 'sucursal_nombre', 'tipodocumentoid',
                  'tipo_documento_nombre', 'urlarchivo', 'fechasubida']