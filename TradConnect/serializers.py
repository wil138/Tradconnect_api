# # serializers.py - Versión Corregida para TradConnect
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from .models import (
    Categoria, Departamento, Municipio, Rol, Moneda, Unidadmedida,
    Estadopedido, Metodopago, Usuario, Empresa, Sucursal, 
    Producto, Pedido, Detallepedido, Factura, Promocion, Inventariobodega,
    Historialestadopedido, Documentosucursal, Tipodocumento
)

# =========================================================
# CATÁLOGOS BASES
# =========================================================
class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombrecategoria', 'descripcion', 'icono', 'colorhex']

class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ['id', 'nombredepartamento']

class MunicipioSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.CharField(source='departamentoid.nombredepartamento', read_only=True)
    class Meta:
        model = Municipio
        fields = ['id', 'nombremunicipio', 'departamentoid', 'departamento_nombre']

class EstadoPedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estadopedido
        fields = ['id', 'estadonombre', 'icono', 'colorhex']

class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Metodopago
        fields = ['id', 'nombremetodo', 'icono', 'descripcion']

class MonedaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Moneda
        fields = ['id', 'nombremoneda', 'simbolo', 'icono']

class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidadmedida
        fields = ['id', 'nombreunidad', 'abreviatura', 'icono']

class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombrerol']

class TipoDocumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tipodocumento
        fields = ['id', 'nombredocumento', 'icono']

# =========================================================
# AUTENTICACIÓN Y USUARIOS
# =========================================================
class UsuarioSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rolid.nombrerol', read_only=True)
    
    class Meta:
        model = Usuario
        fields = ['id', 'rolid', 'rol_nombre', 'nombreusuario', 'correoelectronico', 'fecharegistro']

class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ['id', 'usuarioid', 'rolid', 'razonsocial', 'ruc', 'telefono', 'correoempresa', 'direccionfiscal', 'estado', 'logourl']

class EmpresaRegistroSerializer(serializers.Serializer):
    # Campos del Usuario (Campos exactos en minúsculas)
    nombre_usuario = serializers.CharField(max_length=100)
    correo = serializers.EmailField()
    contrasena = serializers.CharField(write_only=True)
    rol = serializers.ChoiceField(choices=['restaurant', 'provider'])
    
    # Campos de la Empresa
    razon_social = serializers.CharField(max_length=200)
    ruc = serializers.CharField(max_length=50)
    telefono = serializers.CharField(max_length=50)
    direccion_fiscal = serializers.CharField(max_length=250, required=False, allow_blank=True)
    logo_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    def validate_correo(self, value):
        if Usuario.objects.filter(correoelectronico=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

# =========================================================
# NEGOCIO (PRODUCTOS, SUCURSALES, PEDIDOS)
# =========================================================
class SucursalSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(source='municipioid.nombremunicipio', read_only=True)
    class Meta:
        model = Sucursal
        fields = ['id', 'empresaid', 'nombresucursal', 'municipioid', 'municipio_nombre', 
                  'direccionexacta', 'telefonosucursal', 'horarioatencion', 'esbodega', 'estado']

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoriaid.nombrecategoria', read_only=True)
    unidad_nombre = serializers.CharField(source='unidadmedidaid.nombreunidad', read_only=True)
    sucursal_nombre = serializers.CharField(source='sucursalid.nombresucursal', read_only=True)
    stock_disponible = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id', 'sucursalid', 'sucursal_nombre', 'categoriaid', 'categoria_nombre', 
                  'unidadmedidaid', 'unidad_nombre', 'nombreproducto', 'descripcion', 
                  'precioventa', 'cantidadminimapedido', 'esperecedero', 'diasvidautil', 
                  'imagenurl', 'eliminado', 'stock_disponible']

    def get_stock_disponible(self, obj):
        inventario = Inventariobodega.objects.filter(productoid=obj.id).first()
        return float(inventario.stockdisponible) if inventario else 0.0

class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='productoid.nombreproducto', read_only=True)
    class Meta:
        model = Detallepedido
        fields = ['id', 'pedidoid', 'productoid', 'producto_nombre', 'cantidad', 
                  'preciounitario', 'descuentoaplicado', 'subtotal']

class PedidoSerializer(serializers.ModelSerializer):
    restaurante_nombre = serializers.CharField(source='restauranteid.razonsocial', read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedorid.razonsocial', read_only=True)
    estado_nombre = serializers.CharField(source='estadoid.estadonombre', read_only=True)
    estado_color = serializers.CharField(source='estadoid.colorhex', read_only=True)
    estado_icono = serializers.CharField(source='estadoid.icono', read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True, source='detallepedido_set')

    class Meta:
        model = Pedido
        fields = ['id', 'restauranteid', 'restaurante_nombre', 'proveedorid', 'proveedor_nombre', 
                  'sucursalorigenid', 'sucursalentregaid', 'estadoid', 'estado_nombre', 
                  'estado_color', 'estado_icono', 'monedaid', 'metodopagoid', 'subtotal', 
                  'impuesto', 'totalneto', 'comentario', 'fechapedido', 'detalles']

class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = ['id', 'pedidoid', 'numerofactura', 'fechaemision', 
                  'subtotalfactura', 'totalimpuestos', 'totalfacturado', 'icono', 'urlpdf']

class PromocionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promocion
        fields = ['id', 'productoid', 'descripcion', 'cantidadminima', 
                  'porcentajedescuento', 'fechainicio', 'fechafin']

class InventarioBodegaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='productoid.nombreproducto', read_only=True)
    class Meta:
        model = Inventariobodega
        fields = ['productoid', 'sucursalid', 'producto_nombre', 'stockdisponible', 
                  'stockminimo', 'ultimaactualizacion']

class HistorialEstadoPedidoSerializer(serializers.ModelSerializer):
    estado_nombre = serializers.CharField(source='estadoid.estadonombre', read_only=True)
    class Meta:
        model = Historialestadopedido
        fields = ['id', 'pedidoid', 'estadoid', 'estado_nombre', 'comentario', 'fechacambio']

class DocumentoSucursalSerializer(serializers.ModelSerializer):
    sucursal_nombre = serializers.CharField(source='sucursalid.nombresucursal', read_only=True)
    tipo_documento_nombre = serializers.CharField(source='tipodocumentoid.nombredocumento', read_only=True)
    class Meta:
        model = Documentosucursal
        fields = ['id', 'sucursalid', 'sucursal_nombre', 'tipodocumentoid', 'tipo_documento_nombre', 'urlarchivo', 'fechasubida']