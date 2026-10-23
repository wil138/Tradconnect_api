"""Modelos del esquema SQL real. Identidades y empresas residen en MongoDB."""
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class SqlCategoria(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombrecategoria = models.CharField(db_column='NombreCategoria', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    colorhex = models.CharField(db_column='ColorHex', max_length=7, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Categoria'


class SqlUnidadmedida(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombreunidad = models.CharField(db_column='NombreUnidad', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    abreviatura = models.CharField(db_column='Abreviatura', max_length=10, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'UnidadMedida'


class SqlDepartamento(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombredepartamento = models.CharField(db_column='NombreDepartamento', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Departamento'


class SqlEstadopedido(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    estadonombre = models.CharField(db_column='EstadoNombre', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    orden = models.IntegerField(db_column='Orden')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    colorhex = models.CharField(db_column='ColorHex', max_length=7, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'EstadoPedido'


class SqlMetodopago(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombremetodo = models.CharField(db_column='NombreMetodo', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MetodoPago'


class SqlMoneda(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombremoneda = models.CharField(db_column='NombreMoneda', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    simbolo = models.CharField(db_column='Simbolo', max_length=10, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Moneda'


class SqlTipodocumento(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombredocumento = models.CharField(db_column='NombreDocumento', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'TipoDocumento'


class SqlMunicipio(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    departamentoid = models.ForeignKey(SqlDepartamento, models.DO_NOTHING, db_column='DepartamentoId')  # Field name made lowercase.
    nombremunicipio = models.CharField(db_column='NombreMunicipio', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Municipio'


class SqlSucursal(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    empresaid = models.CharField(db_column='EmpresaId', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    codigosucursal = models.CharField(db_column='CodigoSucursal', max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    nombresucursal = models.CharField(db_column='NombreSucursal', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    municipioid = models.ForeignKey(SqlMunicipio, models.DO_NOTHING, db_column='MunicipioId')  # Field name made lowercase.
    direccionexacta = models.CharField(db_column='DireccionExacta', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    telefonosucursal = models.CharField(db_column='TelefonoSucursal', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    horarioatencion = models.CharField(db_column='HorarioAtencion', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    esbodega = models.BooleanField(db_column='EsBodega', blank=True, null=True)  # Field name made lowercase.
    estado = models.CharField(db_column='Estado', max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    fecharegistro = models.DateTimeField(db_column='FechaRegistro')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Sucursal'


class SqlProducto(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    empresaid = models.CharField(db_column='EmpresaId', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    categoriaid = models.ForeignKey(SqlCategoria, models.DO_NOTHING, db_column='CategoriaId')  # Field name made lowercase.
    unidadmedidaid = models.ForeignKey(SqlUnidadmedida, models.DO_NOTHING, db_column='UnidadMedidaId')  # Field name made lowercase.
    nombreproducto = models.CharField(db_column='NombreProducto', max_length=150, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=1000, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    precioventa = models.DecimalField(db_column='PrecioVenta', max_digits=12, decimal_places=2)  # Field name made lowercase.
    cantidadminimapedido = models.IntegerField(db_column='CantidadMinimaPedido')  # Field name made lowercase.
    esperecedero = models.BooleanField(db_column='EsPerecedero', blank=True, null=True)  # Field name made lowercase.
    diasvidautil = models.IntegerField(db_column='DiasVidaUtil', blank=True, null=True)  # Field name made lowercase.
    imagenurl = models.CharField(db_column='ImagenURL', max_length=2048, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    eliminado = models.BooleanField(db_column='Eliminado')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Producto'


class SqlDocumentosucursal(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    sucursalid = models.ForeignKey(SqlSucursal, models.DO_NOTHING, db_column='SucursalId')  # Field name made lowercase.
    tipodocumentoid = models.ForeignKey(SqlTipodocumento, models.DO_NOTHING, db_column='TipoDocumentoId')  # Field name made lowercase.
    urlarchivo = models.CharField(db_column='UrlArchivo', max_length=2048, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    fechasubida = models.DateTimeField(db_column='FechaSubida')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'DocumentoSucursal'


class SqlInventariobodega(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    productoid = models.ForeignKey(SqlProducto, models.DO_NOTHING, db_column='ProductoId')  # Field name made lowercase.
    sucursalid = models.ForeignKey(SqlSucursal, models.DO_NOTHING, db_column='SucursalId')  # Field name made lowercase.
    stockdisponible = models.DecimalField(db_column='StockDisponible', max_digits=12, decimal_places=2)  # Field name made lowercase.
    stockminimo = models.DecimalField(db_column='StockMinimo', max_digits=12, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    ultimaactualizacion = models.DateTimeField(db_column='UltimaActualizacion', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'InventarioBodega'


class SqlPromocion(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    productoid = models.ForeignKey(SqlProducto, models.DO_NOTHING, db_column='ProductoId')  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    cantidadminima = models.IntegerField(db_column='CantidadMinima')  # Field name made lowercase.
    porcentajedescuento = models.DecimalField(db_column='PorcentajeDescuento', max_digits=5, decimal_places=2)  # Field name made lowercase.
    fechainicio = models.DateField(db_column='FechaInicio')  # Field name made lowercase.
    fechafin = models.DateField(db_column='FechaFin')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Promocion'


class SqlPedido(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    restauranteid = models.CharField(db_column='RestauranteId', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    proveedorid = models.CharField(db_column='ProveedorId', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    sucursaloriginalid = models.ForeignKey(SqlSucursal, models.DO_NOTHING, db_column='SucursalOriginalId')  # Field name made lowercase.
    sucursalentregaid = models.ForeignKey(SqlSucursal, models.DO_NOTHING, db_column='SucursalEntregaId', related_name='pedido_sucursalentregaid_set')  # Field name made lowercase.
    monedaid = models.ForeignKey(SqlMoneda, models.DO_NOTHING, db_column='MonedaId')  # Field name made lowercase.
    metodopagoid = models.ForeignKey(SqlMetodopago, models.DO_NOTHING, db_column='MetodoPagoId')  # Field name made lowercase.
    estadopedidoid = models.ForeignKey(SqlEstadopedido, models.DO_NOTHING, db_column='EstadoPedidoId')  # Field name made lowercase.
    subtotal = models.DecimalField(db_column='Subtotal', max_digits=12, decimal_places=2)  # Field name made lowercase.
    impuesto = models.DecimalField(db_column='Impuesto', max_digits=12, decimal_places=2)  # Field name made lowercase.
    totalneto = models.DecimalField(db_column='TotalNeto', max_digits=12, decimal_places=2)  # Field name made lowercase.
    comentario = models.CharField(db_column='Comentario', max_length=500, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    fechapedido = models.DateTimeField(db_column='FechaPedido')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Pedido'


class SqlDetallepedido(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    pedidoid = models.ForeignKey(SqlPedido, models.DO_NOTHING, db_column='PedidoId')  # Field name made lowercase.
    productoid = models.ForeignKey(SqlProducto, models.DO_NOTHING, db_column='ProductoId')  # Field name made lowercase.
    cantidad = models.DecimalField(db_column='Cantidad', max_digits=12, decimal_places=2)  # Field name made lowercase.
    preciounitario = models.DecimalField(db_column='PrecioUnitario', max_digits=12, decimal_places=2)  # Field name made lowercase.
    montodescuento = models.DecimalField(db_column='MontoDescuento', max_digits=12, decimal_places=2)  # Field name made lowercase.
    subtotallinea = models.DecimalField(db_column='SubtotalLinea', max_digits=12, decimal_places=2)  # Field name made lowercase.
    impuestolinea = models.DecimalField(db_column='ImpuestoLinea', max_digits=12, decimal_places=2)  # Field name made lowercase.
    totalnetolinea = models.DecimalField(db_column='TotalNetoLinea', max_digits=12, decimal_places=2)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'DetallePedido'
