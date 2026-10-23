from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers
from . import sql_models as m
from .identities import company_names


def model_serializer(model):
    meta=type('Meta', (), {'model':model, 'fields':'__all__'})
    return type(model.__name__+'Serializer', (serializers.ModelSerializer,), {'Meta':meta})


class BranchSerializer(serializers.ModelSerializer):
    estado=serializers.ChoiceField(choices=['Activo','Inactivo'],required=False)
    municipio_nombre=serializers.CharField(source='municipioid.nombremunicipio', read_only=True)
    class Meta:
        model=m.SqlSucursal
        fields='__all__'
        read_only_fields=('empresaid','codigosucursal','fecharegistro')


    def to_representation(self,instance):
        data=super().to_representation(instance)
        data['estado']='Activo' if (instance.estado or '').casefold() in ('activo','activa') else 'Inactivo'
        return data


class InventorySerializer(serializers.ModelSerializer):
    producto_nombre=serializers.CharField(source='productoid.nombreproducto', read_only=True)
    sucursal_nombre=serializers.CharField(source='sucursalid.nombresucursal', read_only=True)
    class Meta:
        model=m.SqlInventariobodega
        fields='__all__'
        read_only_fields=('ultimaactualizacion',)
    def validate_stockdisponible(self, value):
        if value<0: raise serializers.ValidationError('El stock no puede ser negativo.')
        return value


class ProductSerializer(serializers.ModelSerializer):
    empresa_id=serializers.CharField(source='empresaid',read_only=True)
    empresa_nombre=serializers.SerializerMethodField()
    categoria_nombre=serializers.CharField(source='categoriaid.nombrecategoria',read_only=True)
    unidad_nombre=serializers.CharField(source='unidadmedidaid.nombreunidad',read_only=True)
    inventario=serializers.SerializerMethodField()
    promociones=serializers.SerializerMethodField()
    precio_original=serializers.DecimalField(source='precioventa',max_digits=12,decimal_places=2,read_only=True)
    precio_final=serializers.SerializerMethodField()
    descuento=serializers.SerializerMethodField()
    promocion_activa=serializers.SerializerMethodField()
    sucursal_origen_id=serializers.SerializerMethodField()
    stock_disponible=serializers.DecimalField(max_digits=12,decimal_places=2,min_value=0,write_only=True,required=False)
    stock_inicial=serializers.DecimalField(max_digits=12,decimal_places=2,min_value=0,write_only=True,required=False)
    sucursal_id=serializers.IntegerField(write_only=True,required=False)
    class Meta:
        model=m.SqlProducto
        fields='__all__'
        read_only_fields=('empresaid','eliminado')
        extra_kwargs={'cantidadminimapedido':{'required':False, 'min_value':1}, 'precioventa':{'min_value':Decimal('0.01')}}
    def get_empresa_nombre(self,obj):
        cache=self.context.setdefault('company_names',{})
        if obj.empresaid not in cache: cache.update(company_names([obj.empresaid]))
        return cache.get(obj.empresaid,'Proveedor')
    def get_inventario(self,obj):
        return [{'sucursal_id':i.sucursalid_id,'sucursal_nombre':i.sucursalid.nombresucursal,
            'stock':float(i.stockdisponible),'direccion':i.sucursalid.direccionexacta,
            'telefono':i.sucursalid.telefonosucursal,'horario':i.sucursalid.horarioatencion}
            for i in obj.sqlinventariobodega_set.all() if i.stockdisponible>0 and (i.sucursalid.estado or '').casefold() in ('activo','activa')]
    def get_promociones(self,obj):
        today=timezone.localdate()
        return [{'id':p.pk,'porcentaje_descuento':float(p.porcentajedescuento), 'cantidad_minima':p.cantidadminima,
            'descripcion':p.descripcion,'fecha_inicio':p.fechainicio,'fecha_fin':p.fechafin}
            for p in obj.sqlpromocion_set.all() if p.fechainicio<=today<=p.fechafin]
    def get_descuento(self,obj):
        return max([p['porcentaje_descuento'] for p in self.get_promociones(obj) if p['cantidad_minima']<=obj.cantidadminimapedido] or [0])
    def get_precio_final(self,obj):
        return float((obj.precioventa*(1-Decimal(str(self.get_descuento(obj)))/100)).quantize(Decimal('.01')))
    def get_promocion_activa(self,obj): return bool(self.get_descuento(obj))
    def get_sucursal_origen_id(self,obj):
        inventory=self.get_inventario(obj)
        return inventory[0]['sucursal_id'] if inventory else None


class DetailSerializer(serializers.ModelSerializer):
    producto_nombre=serializers.CharField(source='productoid.nombreproducto',read_only=True)
    subtotal=serializers.DecimalField(source='subtotallinea',max_digits=12,decimal_places=2,read_only=True)
    descuentoaplicado=serializers.SerializerMethodField()
    class Meta:
        model=m.SqlDetallepedido
        fields='__all__'
    def get_descuentoaplicado(self,obj):
        base=obj.cantidad*obj.preciounitario
        return float(obj.montodescuento/base*100) if base else 0


class OrderSerializer(serializers.ModelSerializer):
    detalles=DetailSerializer(source='sqldetallepedido_set',many=True,read_only=True)
    sucursalorigenid=serializers.IntegerField(source='sucursaloriginalid_id',read_only=True)
    restaurante_nombre=serializers.SerializerMethodField()
    proveedor_nombre=serializers.SerializerMethodField()
    estado_actual=serializers.CharField(source='estadopedidoid.estadonombre',read_only=True)
    estado_color=serializers.CharField(source='estadopedidoid.colorhex',read_only=True)
    estado_icono=serializers.CharField(source='estadopedidoid.icono',read_only=True)
    tiene_factura=serializers.SerializerMethodField()
    class Meta:
        model=m.SqlPedido
        fields='__all__'
    def name(self,id):
        cache=self.context.setdefault('company_names',{})
        if id not in cache: cache.update(company_names([id]))
        return cache.get(id,'Empresa')
    def get_restaurante_nombre(self,obj): return self.name(obj.restauranteid)
    def get_proveedor_nombre(self,obj): return self.name(obj.proveedorid)
    def get_tiene_factura(self,obj): return obj.estadopedidoid.estadonombre.casefold()=='completado'
