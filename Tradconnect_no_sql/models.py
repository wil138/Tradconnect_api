"""Modelos documentales Pydantic; no crean tablas SQL."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field, create_model, model_validator

# Catálogos provisionales hasta confirmar los valores del dominio.
class TipoEmpresa(str, Enum):
    RESTAURANTE = 'Restaurante'
    PROVEEDOR = 'Proveedor'
    INTERNA = 'Interna'
    INTERNO = 'Interno'

class NombreRol(str, Enum):
    CLIENTE = 'Cliente'
    PROVEEDOR = 'Proveedor'
    ADMINISTRADOR = 'Administrador'
    ADMIN = 'Admin'
    ANALISTA = 'Analista'
    GERENCIA = 'Gerencia'

class EstadoIncidencia(str, Enum):
    PENDIENTE = 'Pendiente'
    EN_PROCESO = 'En proceso'
    RESUELTA = 'Resuelta'

class EstadoNecesidad(str, Enum):
    PENDIENTE = 'Pendiente'
    EN_PROCESO = 'En proceso'
    SATISFECHA = 'Satisfecha'

class DocumentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class UsuarioEmpresaRolBase(DocumentCreate):
    empresa_id: str | None = None
    razon_social: str | None = None
    ruc: str | None = None
    tipo_empresa: TipoEmpresa
    telefono_empresa: str | None = None
    direccion_fiscal: str | None = None
    usuario_id: str
    nombre_usuario: str
    correo: EmailStr
    password_hash: str
    estado_usuario: bool
    rol_id: int
    nombre_rol: NombreRol
    sucursal_id_sql: int | None = None
    estado_rol: bool
    fecha_asignacion: datetime
    fecha_registro: datetime
    ambito: str | None = None
    responsabilidades: list[str] | None = None
    empresas_asignadas: list[str] | None = None
    datos_demo: bool | None = None

    @model_validator(mode='after')
    def validar_vinculo_empresa(self):
        expected = {'Cliente': 'Restaurante', 'Proveedor': 'Proveedor'}.get(self.nombre_rol.value)
        if expected and (self.tipo_empresa.value != expected or not self.empresa_id or not self.razon_social or not self.ruc):
            raise ValueError(f'El rol {self.nombre_rol.value} requiere una empresa {expected} completa.')
        if self.sucursal_id_sql is not None and not self.empresa_id:
            raise ValueError('Una sucursal requiere una empresa asociada.')
        return self

class UsuarioEmpresaRolCreate(UsuarioEmpresaRolBase):
    pass

class UsuarioEmpresaRolRead(UsuarioEmpresaRolBase):
    id: str = Field(alias='_id')
    correo: str
    password_hash: str | None = Field(default=None, exclude=True)
    model_config = ConfigDict(populate_by_name=True, extra='ignore', allow_inf_nan=False)

class PreferenciaNegocioCreate(DocumentCreate):
    empresa_id: str
    usuario_id: str
    horario_entrega_preferido: str
    fecha_actualizacion: datetime

class PreferenciaCategoriaCreate(DocumentCreate):
    preferencia_id: str
    categoria_id_sql: int

class PreferenciaProductoCreate(DocumentCreate):
    preferencia_id: str
    producto_id_sql: int
    nombre: str

class PreferenciaMetodoPagoCreate(DocumentCreate):
    preferencia_id: str
    metodo_pago_id_sql: int

class EvaluacionProveedorCreate(DocumentCreate):
    pedido_id_sql: int
    cliente_empresa_id: str
    cliente_nombre: str
    cliente_sucursal_id_sql: int | None = None
    proveedor_empresa_id: str
    proveedor_nombre: str
    proveedor_sucursal_id_sql: int | None = None
    puntuacion: float = Field(ge=1, le=5)
    calidad: int = Field(ge=1, le=5)
    tiempo_entrega: int = Field(ge=1, le=5)
    precio: int = Field(ge=1, le=5)
    atencion: int = Field(ge=1, le=5)
    comentario: str | None = None
    fecha: datetime

class TransaccionNoExitosaCreate(DocumentCreate):
    fecha_intento: datetime
    pedido_id_sql: int | None = None
    cliente_empresa_id: str
    cliente_nombre: str
    proveedor_empresa_id: str
    proveedor_nombre: str
    motivo: str
    monto_tentativo: Decimal = Field(ge=0)

class SustitucionOfrecidaCreate(DocumentCreate):
    transaccion_id: str
    producto_solicitado: str
    producto_alternativo_ofrecido: str

class IncidenciaEntregaCreate(DocumentCreate):
    respuesta_proveedor: str | None = None
    fecha_respuesta: datetime | None = None
    pedido_id_sql: int
    cliente_empresa_id: str
    cliente_nombre: str
    proveedor_empresa_id: str
    proveedor_nombre: str
    tipo_incidencia: str
    tipo_reclamo: str
    estado: EstadoIncidencia
    fecha: datetime

class EvidenciaIncidenciaCreate(DocumentCreate):
    incidencia_id: str
    nombre_archivo: str
    url: str

class ComentarioPostCompraCreate(DocumentCreate):
    pedido_id_sql: int
    cliente_empresa_id: str
    cliente_nombre: str
    proveedor_empresa_id: str
    proveedor_nombre: str
    opinion_libre: str
    calificacion: int = Field(ge=1, le=5)
    fecha: datetime

class InteraccionComentarioCreate(DocumentCreate):
    comentario_id: str
    fecha: datetime
    tipo: str
    mensaje: str
    usuario_id: str

class NecesidadNoSatisfechaCreate(DocumentCreate):
    cliente_empresa_id: str
    cliente_nombre: str
    insumo_buscado: str
    cantidades_requeridas: int = Field(ge=1)
    unidad: str
    categoria_id_sql: int
    estado: EstadoNecesidad
    fecha: datetime

SCHEMAS = {}
for collection, schema in {
    'usuarios_empresas_roles': UsuarioEmpresaRolCreate,
    'preferencias_negocio': PreferenciaNegocioCreate,
    'preferencias_categorias': PreferenciaCategoriaCreate,
    'preferencias_productos': PreferenciaProductoCreate,
    'preferencias_metodos_pago': PreferenciaMetodoPagoCreate,
    'evaluaciones_proveedores': EvaluacionProveedorCreate,
    'transacciones_no_exitosas': TransaccionNoExitosaCreate,
    'sustituciones_ofrecidas': SustitucionOfrecidaCreate,
    'incidencias_entregas': IncidenciaEntregaCreate,
    'evidencias_incidencia': EvidenciaIncidenciaCreate,
    'comentarios_post_compra': ComentarioPostCompraCreate,
    'interacciones_comentario': InteraccionComentarioCreate,
    'necesidades_no_satisfechas': NecesidadNoSatisfechaCreate,
}.items():
    read_name = schema.__name__.removesuffix('Create') + 'Read'
    if collection == 'usuarios_empresas_roles':
        read_schema = UsuarioEmpresaRolRead
    else:
        read_schema = create_model(read_name, __base__=schema, id=(str, Field(alias='_id')))
        read_schema.model_config = ConfigDict(populate_by_name=True, extra='ignore', allow_inf_nan=False)
        read_schema.model_rebuild(force=True)
        globals()[read_name] = read_schema
    SCHEMAS[collection] = (schema, read_schema)
