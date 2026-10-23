"""Compatibilidad con instalaciones SQL antiguas. La API HTTP actual usa sql_models.py, hybrid_views.py e identities.py; ver urls.py."""
# serializers.py - TradConnect (sin catálogos expuestos, sin Factura)
from django.db import models
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
    correo = serializers.EmailField(max_length=150)
    contrasena = serializers.CharField(write_only=True, min_length=8, max_length=128, trim_whitespace=False)
    rol = serializers.ChoiceField(choices=[('restaurant', 'Restaurante'), ('provider', 'Proveedor')])
    razon_social = serializers.CharField(max_length=150)
    ruc = serializers.CharField(max_length=50)
    telefono = serializers.CharField(max_length=50)
    direccion_fiscal = serializers.CharField(max_length=250, required=False, allow_blank=True)
    logo_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    def validate_correo(self, value):
        if Usuario.objects.filter(correoelectronico__iexact=value).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value

    def validate_nombre_usuario(self, value):
        if Usuario.objects.filter(nombreusuario__iexact=value).exists():
            raise serializers.ValidationError("Este usuario ya está registrado.")
        return value

    def validate_ruc(self, value):
        if Empresa.objects.filter(ruc__iexact=value).exists():
            raise serializers.ValidationError("Este RUC ya está registrado.")
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
    empresa_id = serializers.IntegerField(source='empresaid.id', read_only=True)
    empresa_nombre = serializers.CharField(source='empresaid.razonsocial', read_only=True)
    inventario = serializers.SerializerMethodField()
    promociones = serializers.SerializerMethodField()
    categoria_nombre = serializers.CharField(source='categoriaid.nombrecategoria', read_only=True)
    unidad_nombre = serializers.CharField(source='unidadmedidaid.nombreunidad', read_only=True)
    
    # Campos para marketplace (precio con descuento, etc.)
    precio_final = serializers.SerializerMethodField()
    precio_original = serializers.SerializerMethodField()
    descuento = serializers.SerializerMethodField()
    promocion_activa = serializers.SerializerMethodField()
    sucursal_origen_id = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id', 'empresa_id', 'empresa_nombre',
            'nombreproducto', 'descripcion', 'precioventa',
            'imagenurl', 'categoria_nombre', 'unidad_nombre',
            'esperecedero', 'diasvidautil',
            'inventario', 'promociones',
            'precio_final', 'precio_original', 'descuento', 'promocion_activa',
            'sucursal_origen_id'
        ]

    def get_inventario(self, obj):
        inventario_qs = Inventariobodega.objects.filter(
            productoid=obj,
            stockdisponible__gt=0,
            sucursalid__estado__iexact='activo'
        ).select_related('sucursalid')
        return [
            {
                'sucursal_id': inv.sucursalid.id,
                'sucursal_nombre': inv.sucursalid.nombresucursal,
                'direccion': inv.sucursalid.direccionexacta,
                'telefono': inv.sucursalid.telefonosucursal,
                'horario': inv.sucursalid.horarioatencion,
                'stock': float(inv.stockdisponible),
                'stock_minimo': float(inv.stockminimo) if inv.stockminimo else None,
            }
            for inv in inventario_qs
        ]

    def get_promociones(self, obj):
        hoy = timezone.now().date()
        promociones_qs = Promocion.objects.filter(
            productoid=obj,
            fechainicio__lte=hoy,
            fechafin__gte=hoy
        )
        return [
            {
                'id': p.id,
                'descripcion': p.descripcion,
                'porcentaje_descuento': float(p.porcentajedescuento),
                'cantidad_minima': p.cantidadminima,
                'fecha_inicio': p.fechainicio,
                'fecha_fin': p.fechafin,
            }
            for p in promociones_qs
        ]

    def get_precio_final(self, obj):
        """Precio con el mayor descuento aplicable (si hay promoción activa)"""
        promociones = self.get_promociones(obj)
        if promociones:
            # Tomar el mayor descuento
            max_descuento = max(p['porcentaje_descuento'] for p in promociones)
            return float(obj.precioventa) * (1 - max_descuento / 100)
        return float(obj.precioventa)

    def get_precio_original(self, obj):
        return float(obj.precioventa)

    def get_descuento(self, obj):
        promociones = self.get_promociones(obj)
        if promociones:
            max_descuento = max(p['porcentaje_descuento'] for p in promociones)
            return max_descuento
        return 0

    def get_promocion_activa(self, obj):
        return bool(self.get_promociones(obj))

    def get_sucursal_origen_id(self, obj):
        """Devuelve la primera sucursal con stock como origen (para el carrito)"""
        inventario = self.get_inventario(obj)
        if inventario:
            return inventario[0]['sucursal_id']
        return None

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
    tiene_factura = serializers.SerializerMethodField()

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

# =========================================================
# SERIALIZERS PÚBLICOS (para marketplace)
# =========================================================
class PublicSucursalSerializer(serializers.ModelSerializer):
    municipio_nombre = serializers.CharField(source='municipioid.nombremunicipio', read_only=True)
    class Meta:
        model = Sucursal
        fields = ['id', 'nombresucursal', 'direccionexacta', 'telefonosucursal',
                  'horarioatencion', 'municipio_nombre', 'estado']

class PublicInventarioSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='productoid.nombreproducto', read_only=True)
    producto_precio = serializers.DecimalField(source='productoid.precioventa', read_only=True, max_digits=12, decimal_places=2)
    producto_imagen = serializers.CharField(source='productoid.imagenurl', read_only=True)
    sucursal_nombre = serializers.CharField(source='sucursalid.nombresucursal', read_only=True)
    class Meta:
        model = Inventariobodega
        fields = ['id', 'producto_nombre', 'producto_precio', 'producto_imagen',
                  'sucursal_nombre', 'stockdisponible', 'stockminimo']

class PublicPromocionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='productoid.nombreproducto', read_only=True)
    class Meta:
        model = Promocion
        fields = ['id', 'producto_nombre', 'descripcion', 'porcentajedescuento',
                  'fechainicio', 'fechafin']