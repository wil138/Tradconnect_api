# python manage.py inspectdb > /models.py                     
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Categoria(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombrecategoria = models.CharField(db_column='NombreCategoria', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    colorhex = models.CharField(db_column='ColorHex', max_length=7, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Categoria'


class Departamento(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombredepartamento = models.CharField(db_column='NombreDepartamento', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Departamento'


class Detallepedido(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    pedidoid = models.ForeignKey('Pedido', models.DO_NOTHING, db_column='PedidoId')  # Field name made lowercase.
    productoid = models.ForeignKey('Producto', models.DO_NOTHING, db_column='ProductoId')  # Field name made lowercase.
    cantidad = models.DecimalField(db_column='Cantidad', max_digits=12, decimal_places=2)  # Field name made lowercase.
    preciounitario = models.DecimalField(db_column='PrecioUnitario', max_digits=12, decimal_places=2)  # Field name made lowercase.
    descuentoaplicado = models.DecimalField(db_column='DescuentoAplicado', max_digits=5, decimal_places=2, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'DetallePedido'


class Documentosucursal(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    sucursalid = models.ForeignKey('Sucursal', models.DO_NOTHING, db_column='SucursalId')  # Field name made lowercase.
    tipodocumentoid = models.ForeignKey('Tipodocumento', models.DO_NOTHING, db_column='TipoDocumentoId')  # Field name made lowercase.
    urlarchivo = models.CharField(db_column='UrlArchivo', max_length=2048, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    fechasubida = models.DateTimeField(db_column='FechaSubida')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'DocumentoSucursal'


class Empresa(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    usuarioid = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='UsuarioId')  # Field name made lowercase.
    rolid = models.ForeignKey('Rol', models.DO_NOTHING, db_column='RolId')  # Field name made lowercase.
    razonsocial = models.CharField(db_column='RazonSocial', max_length=150, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    ruc = models.CharField(db_column='RUC', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    telefono = models.CharField(db_column='Telefono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    correoempresa = models.CharField(db_column='CorreoEmpresa', max_length=150, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    direccionfiscal = models.CharField(db_column='DireccionFiscal', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    estado = models.BooleanField(db_column='Estado', blank=True, null=True)  # Field name made lowercase.
    logourl = models.CharField(db_column='LogoUrl', max_length=500, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Empresa'


class Estadopedido(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    estadonombre = models.CharField(db_column='EstadoNombre', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    orden = models.IntegerField(db_column='Orden')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    colorhex = models.CharField(db_column='ColorHex', max_length=7, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'EstadoPedido'


class Historialestadopedido(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    pedidoid = models.ForeignKey('Pedido', models.DO_NOTHING, db_column='PedidoId')  # Field name made lowercase.
    estadoid = models.ForeignKey(Estadopedido, models.DO_NOTHING, db_column='EstadoId')  # Field name made lowercase.
    comentario = models.CharField(db_column='Comentario', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    fechacambio = models.DateTimeField(db_column='FechaCambio')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'HistorialEstadoPedido'


class Inventariobodega(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    productoid = models.ForeignKey('Producto', models.DO_NOTHING, db_column='ProductoId')  # Field name made lowercase.
    sucursalid = models.ForeignKey('Sucursal', models.DO_NOTHING, db_column='SucursalId')  # Field name made lowercase.
    stockdisponible = models.DecimalField(db_column='StockDisponible', max_digits=12, decimal_places=2)  # Field name made lowercase.
    stockminimo = models.DecimalField(db_column='StockMinimo', max_digits=12, decimal_places=2, blank=True, null=True)  # Field name made lowercase.
    ultimaactualizacion = models.DateTimeField(db_column='UltimaActualizacion', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'InventarioBodega'


class Metodopago(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombremetodo = models.CharField(db_column='NombreMetodo', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'MetodoPago'


class Moneda(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombremoneda = models.CharField(db_column='NombreMoneda', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    simbolo = models.CharField(db_column='Simbolo', max_length=10, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Moneda'


class Municipio(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    departamentoid = models.ForeignKey(Departamento, models.DO_NOTHING, db_column='DepartamentoId')  # Field name made lowercase.
    nombremunicipio = models.CharField(db_column='NombreMunicipio', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Municipio'


class Pedido(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    restauranteid = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='RestauranteId')  # Field name made lowercase.
    proveedorid = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='ProveedorId', related_name='pedido_proveedorid_set')  # Field name made lowercase.
    sucursalorigenid = models.ForeignKey('Sucursal', models.DO_NOTHING, db_column='SucursalOrigenId')  # Field name made lowercase.
    sucursalentregaid = models.ForeignKey('Sucursal', models.DO_NOTHING, db_column='SucursalEntregaId', related_name='pedido_sucursalentregaid_set')  # Field name made lowercase.
    monedaid = models.ForeignKey(Moneda, models.DO_NOTHING, db_column='MonedaId')  # Field name made lowercase.
    metodopagoid = models.ForeignKey(Metodopago, models.DO_NOTHING, db_column='MetodoPagoId')  # Field name made lowercase.
    subtotal = models.DecimalField(db_column='Subtotal', max_digits=12, decimal_places=2)  # Field name made lowercase.
    impuesto = models.DecimalField(db_column='Impuesto', max_digits=12, decimal_places=2)  # Field name made lowercase.
    totalneto = models.DecimalField(db_column='TotalNeto', max_digits=12, decimal_places=2)  # Field name made lowercase.
    comentario = models.CharField(db_column='Comentario', max_length=500, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    fechapedido = models.DateTimeField(db_column='FechaPedido')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Pedido'


class Producto(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    empresaid = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='EmpresaId')  # Field name made lowercase.
    categoriaid = models.ForeignKey(Categoria, models.DO_NOTHING, db_column='CategoriaId')  # Field name made lowercase.
    unidadmedidaid = models.ForeignKey('Unidadmedida', models.DO_NOTHING, db_column='UnidadMedidaId')  # Field name made lowercase.
    nombreproducto = models.CharField(db_column='NombreProducto', max_length=150, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=1000, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    precioventa = models.DecimalField(db_column='PrecioVenta', max_digits=12, decimal_places=2)  # Field name made lowercase.
    cantidadminimapedido = models.IntegerField(db_column='CantidadMinimaPedido')  # Field name made lowercase.
    esperecedero = models.BooleanField(db_column='EsPerecedero', blank=True, null=True)  # Field name made lowercase.
    diasvidautil = models.IntegerField(db_column='DiasVidaUtil', blank=True, null=True)  # Field name made lowercase.
    imagenurl = models.CharField(db_column='ImagenUrl', max_length=2048, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    eliminado = models.BooleanField(db_column='Eliminado')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Producto'


class Promocion(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    productoid = models.ForeignKey(Producto, models.DO_NOTHING, db_column='ProductoId')  # Field name made lowercase.
    descripcion = models.CharField(db_column='Descripcion', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    cantidadminima = models.IntegerField(db_column='CantidadMinima')  # Field name made lowercase.
    porcentajedescuento = models.DecimalField(db_column='PorcentajeDescuento', max_digits=5, decimal_places=2)  # Field name made lowercase.
    fechainicio = models.DateField(db_column='FechaInicio')  # Field name made lowercase.
    fechafin = models.DateField(db_column='FechaFin')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Promocion'


class Rol(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombrerol = models.CharField(db_column='NombreRol', unique=True, max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Rol'


class Sucursal(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    empresaid = models.ForeignKey(Empresa, models.DO_NOTHING, db_column='EmpresaId')  # Field name made lowercase.
    nombresucursal = models.CharField(db_column='NombreSucursal', max_length=150, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    municipioid = models.ForeignKey(Municipio, models.DO_NOTHING, db_column='MunicipioId')  # Field name made lowercase.
    direccionexacta = models.CharField(db_column='DireccionExacta', max_length=250, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    telefonosucursal = models.CharField(db_column='TelefonoSucursal', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    horarioatencion = models.CharField(db_column='HorarioAtencion', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    esbodega = models.BooleanField(db_column='EsBodega', blank=True, null=True)  # Field name made lowercase.
    estado = models.CharField(db_column='Estado', max_length=20, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    fecharegistro = models.DateTimeField(db_column='FechaRegistro')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Sucursal'


class Tipodocumento(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombredocumento = models.CharField(db_column='NombreDocumento', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'TipoDocumento'


class Unidadmedida(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    nombreunidad = models.CharField(db_column='NombreUnidad', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    abreviatura = models.CharField(db_column='Abreviatura', max_length=10, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.
    icono = models.CharField(db_column='Icono', max_length=50, db_collation='SQL_Latin1_General_CP1_CI_AS', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'UnidadMedida'


class Usuario(models.Model):
    id = models.AutoField(db_column='Id', primary_key=True)  # Field name made lowercase.
    rolid = models.ForeignKey(Rol, models.DO_NOTHING, db_column='RolId')  # Field name made lowercase.
    nombreusuario = models.CharField(db_column='NombreUsuario', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    correoelectronico = models.CharField(db_column='CorreoElectronico', unique=True, max_length=150, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    contrasena = models.CharField(db_column='Contrasena', max_length=100, db_collation='SQL_Latin1_General_CP1_CI_AS')  # Field name made lowercase.
    fecharegistro = models.DateTimeField(db_column='FechaRegistro')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Usuario'