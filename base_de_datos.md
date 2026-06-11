CREATE DATABASE TC
go
use TC

-- NIVEL 1: TABLAS INDEPENDIENTES (sin FK)

-- 1.1 ROLES
CREATE TABLE Rol (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    NombreRol NVARCHAR(50) NOT NULL UNIQUE
);

-- 1.2 CATEGORÍA (con icono y color)
CREATE TABLE Categoria (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    NombreCategoria NVARCHAR(100) NOT NULL,
    Descripcion NVARCHAR(250),
    Icono NVARCHAR(50) NULL,
    ColorHex NVARCHAR(7) NULL
);

-- 1.3 UNIDAD DE MEDIDA 
CREATE TABLE UnidadMedida (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    NombreUnidad NVARCHAR(50) NOT NULL,
    Abreviatura NVARCHAR(10),
    Icono NVARCHAR(50) NULL
);

-- 1.4 DEPARTAMENTO
CREATE TABLE Departamento (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    NombreDepartamento NVARCHAR(100) NOT NULL
);

-- 1.5 ESTADO DE PEDIDO (con icono y color y orden)
CREATE TABLE EstadoPedido (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    EstadoNombre NVARCHAR(50) NOT NULL,
    Orden INT NOT NULL,
    Icono NVARCHAR(50) NULL,
    ColorHex NVARCHAR(7) NULL
);

-- 1.6 MÉTODO DE PAGO (con icono)
CREATE TABLE MetodoPago (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    NombreMetodo NVARCHAR(50) NOT NULL,
    Icono NVARCHAR(50) NULL,
    Descripcion NVARCHAR(100) NULL
);

-- 1.7 MONEDA (con icono)
CREATE TABLE Moneda (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    NombreMoneda NVARCHAR(50) NOT NULL,
    Simbolo NVARCHAR(10) NOT NULL,
    Icono NVARCHAR(50) NULL
);

-- 1.8 TIPO DE DOCUMENTO (con icono)
CREATE TABLE TipoDocumento (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    NombreDocumento NVARCHAR(50) NOT NULL,
    Icono NVARCHAR(50) NULL
);

-- NIVEL 2: TABLAS QUE DEPENDEN DE NIVEL 1

-- 2.1 USUARIO (depende de Rol)
CREATE TABLE Usuario (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    RolId INT NOT NULL,
    NombreUsuario NVARCHAR(100) NOT NULL,
    CorreoElectronico NVARCHAR(150) NOT NULL UNIQUE,
    Contrasena NVARCHAR(100) NOT NULL,
    FechaRegistro DATETIME DEFAULT GETDATE() NOT NULL,
    CONSTRAINT FK_Usuario_Rol FOREIGN KEY (RolId) REFERENCES Rol(Id)
);

-- 2.2 MUNICIPIO (depende de Departamento)
CREATE TABLE Municipio (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    DepartamentoId INT NOT NULL,
    NombreMunicipio NVARCHAR(100) NOT NULL,
    CONSTRAINT FK_Municipio_Dep FOREIGN KEY (DepartamentoId) REFERENCES Departamento(Id)
);

-- NIVEL 3: TABLAS QUE DEPENDEN DE NIVEL 2

-- 3.1 EMPRESA (depende de Usuario y Rol)
CREATE TABLE Empresa (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    UsuarioId INT NOT NULL,
    RolId INT NOT NULL,
    RazonSocial NVARCHAR(150) NOT NULL,
    RUC NVARCHAR(50) NOT NULL,
    Telefono NVARCHAR(50),
    CorreoEmpresa NVARCHAR(150),
    DireccionFiscal NVARCHAR(250),
    Estado BIT DEFAULT 1,
    LogoUrl NVARCHAR(500) NULL,
    CONSTRAINT FK_Empresa_Usuario FOREIGN KEY (UsuarioId) REFERENCES Usuario(Id),
    CONSTRAINT FK_Empresa_Rol FOREIGN KEY (RolId) REFERENCES Rol(Id)
);

-- 3.2 SUCURSAL (depende de Empresa y Municipio)
CREATE TABLE Sucursal (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    EmpresaId INT NOT NULL,
    NombreSucursal NVARCHAR(150) NOT NULL,
    MunicipioId INT NOT NULL,
    DireccionExacta NVARCHAR(250),
    TelefonoSucursal NVARCHAR(50),
    HorarioAtencion NVARCHAR(100),
    EsBodega BIT DEFAULT 0,
    Estado NVARCHAR(20) DEFAULT 'Activo',
    FechaRegistro DATETIME DEFAULT GETDATE() NOT NULL,
    CONSTRAINT FK_Sucursal_Empresa FOREIGN KEY (EmpresaId) REFERENCES Empresa(Id),
    CONSTRAINT FK_Sucursal_Municipio FOREIGN KEY (MunicipioId) REFERENCES Municipio(Id)
);

-- 3.3 PRODUCTO (depende de Empresa, Categoria, UnidadMedida)
CREATE TABLE Producto (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    EmpresaId INT NOT NULL,  
    CategoriaId INT NOT NULL,
    UnidadMedidaId INT NOT NULL,
    NombreProducto NVARCHAR(150) NOT NULL,
    Descripcion NVARCHAR(1000),
    PrecioVenta DECIMAL(12,2) NOT NULL,
    CantidadMinimaPedido INT DEFAULT 1 NOT NULL,
    EsPerecedero BIT DEFAULT 1,
    DiasVidaUtil INT NULL,
    ImagenUrl NVARCHAR(2048),
    Eliminado BIT DEFAULT 0 NOT NULL,
    CONSTRAINT FK_Prod_Empresa FOREIGN KEY (EmpresaId) REFERENCES Empresa(Id),
    CONSTRAINT FK_Prod_Cat FOREIGN KEY (CategoriaId) REFERENCES Categoria(Id),
    CONSTRAINT FK_Prod_Unidad FOREIGN KEY (UnidadMedidaId) REFERENCES UnidadMedida(Id)
);

-- 3.4 DOCUMENTO SUCURSAL (depende de Sucursal y TipoDocumento)
CREATE TABLE DocumentoSucursal (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    SucursalId INT NOT NULL,
    TipoDocumentoId INT NOT NULL,
    UrlArchivo NVARCHAR(2048) NOT NULL,
    FechaSubida DATETIME DEFAULT GETDATE() NOT NULL,
    CONSTRAINT FK_Doc_Suc FOREIGN KEY (SucursalId) REFERENCES Sucursal(Id),
    CONSTRAINT FK_Doc_Tipo FOREIGN KEY (TipoDocumentoId) REFERENCES TipoDocumento(Id)
);


-- NIVEL 4: TABLAS TRANSACCIONALES

-- 4.1 INVENTARIO BODEGA (se agregó Id y depende de Producto y Sucursal)
CREATE TABLE InventarioBodega (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    ProductoId INT NOT NULL,
    SucursalId INT NOT NULL,
    StockDisponible DECIMAL(12,2) NOT NULL DEFAULT 0,
    StockMinimo DECIMAL(12,2) DEFAULT 0,
    UltimaActualizacion DATETIME DEFAULT GETDATE(),
    CONSTRAINT FK_Inv_Prod FOREIGN KEY (ProductoId) REFERENCES Producto(Id),
    CONSTRAINT FK_Inv_Suc FOREIGN KEY (SucursalId) REFERENCES Sucursal(Id)
);

-- 4.2 PROMOCIÓN (depende de Producto)
CREATE TABLE Promocion (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    ProductoId INT NOT NULL,
    Descripcion NVARCHAR(250),
    CantidadMinima INT NOT NULL,
    PorcentajeDescuento DECIMAL(5,2) NOT NULL,
    FechaInicio DATE NOT NULL,
    FechaFin DATE NOT NULL,
    CONSTRAINT FK_Promo_Prod FOREIGN KEY (ProductoId) REFERENCES Producto(Id)
);

-- 4.3 PEDIDO (depende de Empresa, Sucursal, Moneda, MetodoPago)
-- Se eliminó la conexión con EstadoPedido
CREATE TABLE Pedido (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    RestauranteId INT NOT NULL,
    ProveedorId INT NOT NULL,
    SucursalOrigenId INT NOT NULL,
    SucursalEntregaId INT NOT NULL,
    MonedaId INT NOT NULL,
    MetodoPagoId INT NOT NULL,
    Subtotal DECIMAL(12,2) NOT NULL,
    Impuesto DECIMAL(12,2) NOT NULL,
    TotalNeto DECIMAL(12,2) NOT NULL,
    Comentario NVARCHAR(500),
    FechaPedido DATETIME DEFAULT GETDATE() NOT NULL,
    CONSTRAINT FK_Pedido_Restaurante FOREIGN KEY (RestauranteId) REFERENCES Empresa(Id),
    CONSTRAINT FK_Pedido_Proveedor FOREIGN KEY (ProveedorId) REFERENCES Empresa(Id),
    CONSTRAINT FK_Pedido_SucOri FOREIGN KEY (SucursalOrigenId) REFERENCES Sucursal(Id),
    CONSTRAINT FK_Pedido_SucEnt FOREIGN KEY (SucursalEntregaId) REFERENCES Sucursal(Id),
    CONSTRAINT FK_Pedido_Moneda FOREIGN KEY (MonedaId) REFERENCES Moneda(Id),
    CONSTRAINT FK_Pedido_Metodo FOREIGN KEY (MetodoPagoId) REFERENCES MetodoPago(Id)
);

-- 4.4 DETALLE PEDIDO (depende de Pedido y Producto)
-- Se eliminó el campo Subtotal
CREATE TABLE DetallePedido (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    PedidoId INT NOT NULL,
    ProductoId INT NOT NULL,
    Cantidad DECIMAL(12,2) NOT NULL,
    PrecioUnitario DECIMAL(12,2) NOT NULL,
    DescuentoAplicado DECIMAL(5,2) DEFAULT 0,
    CONSTRAINT FK_Det_Pedido FOREIGN KEY (PedidoId) REFERENCES Pedido(Id),
    CONSTRAINT FK_Det_Prod FOREIGN KEY (ProductoId) REFERENCES Producto(Id)
);


-- 4.6 HISTORIAL ESTADO PEDIDO (depende de Pedido y EstadoPedido)
CREATE TABLE HistorialEstadoPedido (
    Id INT IDENTITY(1,1) PRIMARY KEY,
    PedidoId INT NOT NULL,
    EstadoId INT NOT NULL,
    Comentario NVARCHAR(250),
    FechaCambio DATETIME DEFAULT GETDATE() NOT NULL,
    CONSTRAINT FK_Hist_Pedido FOREIGN KEY (PedidoId) REFERENCES Pedido(Id),
    CONSTRAINT FK_Hist_Estado FOREIGN KEY (EstadoId) REFERENCES EstadoPedido(Id)
);