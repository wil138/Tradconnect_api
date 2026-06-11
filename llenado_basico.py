# llenar_todo.py - Script completo para poblar toda la base de datos
import os
import sys
import random
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from faker import Faker

from TradConnect.models import (
    Rol, Categoria, Unidadmedida, Metodopago, Moneda, Estadopedido,
    Departamento, Municipio, Usuario, Empresa, Sucursal, Producto,
    Inventariobodega, Promocion, Pedido, Detallepedido, Historialestadopedido
)

fake = Faker('es_ES')

def crear_catalogos():
    print("=" * 60)
    print("📦 1. CREANDO CATÁLOGOS BASE")
    print("=" * 60)
    
    # Roles
    rol_rest, _ = Rol.objects.get_or_create(nombrerol='Restaurante')
    rol_prov, _ = Rol.objects.get_or_create(nombrerol='Proveedor')
    print(f"✅ Roles: Restaurante, Proveedor")
    
    # Categorías
    categorias_data = [
        ('Carnes', 'Productos cárnicos frescos y procesados', 'fa-drumstick-bite', '#ef4444'),
        ('Lácteos', 'Lácteos y derivados', 'fa-cheese', '#f59e0b'),
        ('Verduras', 'Verduras frescas', 'fa-carrot', '#10b981'),
        ('Granos', 'Granos básicos y cereales', 'fa-wheat-alt', '#8b5cf6'),
        ('Bebidas', 'Bebidas y jugos', 'fa-wine-bottle', '#3b82f6'),
        ('Panadería', 'Pan y repostería', 'fa-bread-slice', '#d97706'),
        ('Frutas', 'Frutas frescas', 'fa-apple-alt', '#22c55e'),
        ('Especias', 'Especias y condimentos', 'fa-pepper-hot', '#ea580c'),
    ]
    for nombre, desc, icono, color in categorias_data:
        Categoria.objects.get_or_create(
            nombrecategoria=nombre,
            defaults={'descripcion': desc, 'icono': icono, 'colorhex': color}
        )
    print(f"✅ {len(categorias_data)} categorías")
    
    # Unidades de medida
    unidades_data = [
        ('Kilogramo', 'kg', 'fa-weight-hanging'),
        ('Litro', 'L', 'fa-fill-drip'),
        ('Unidad', 'und', 'fa-cube'),
        ('Bolsa', 'bolsa', 'fa-bag-shopping'),
        ('Caja', 'caja', 'fa-box'),
        ('Docena', 'doc', 'fa-egg'),
        ('Gramo', 'g', 'fa-weight-scale'),
        ('Mililitro', 'ml', 'fa-flask'),
    ]
    for nombre, abrev, icono in unidades_data:
        Unidadmedida.objects.get_or_create(
            nombreunidad=nombre,
            defaults={'abreviatura': abrev, 'icono': icono}
        )
    print(f"✅ {len(unidades_data)} unidades de medida")
    
    # Métodos de pago
    metodos_data = [
        ('Transferencia bancaria', 'fa-building-columns', 'Transferencia desde cuenta bancaria'),
        ('Efectivo', 'fa-money-bill', 'Pago en efectivo al recibir'),
        ('Tarjeta de crédito', 'fa-credit-card', 'Visa, Mastercard, American Express'),
        ('Contra entrega', 'fa-truck-fast', 'Pago al momento de la entrega'),
        ('Sinpe Móvil', 'fa-mobile-alt', 'Transferencia mediante Sinpe Móvil'),
    ]
    for nombre, icono, desc in metodos_data:
        Metodopago.objects.get_or_create(
            nombremetodo=nombre,
            defaults={'icono': icono, 'descripcion': desc}
        )
    print(f"✅ {len(metodos_data)} métodos de pago")
    
    # Monedas
    Moneda.objects.get_or_create(nombremoneda='Córdoba', defaults={'simbolo': 'C$', 'icono': 'fa-money-bill'})
    Moneda.objects.get_or_create(nombremoneda='Dólar', defaults={'simbolo': '$', 'icono': 'fa-dollar-sign'})
    print("✅ Monedas: Córdoba, Dólar")
    
    # Estados de pedido
    estados_data = [
        ('Pendiente', 1, 'fa-clock', '#f59e0b', 'Esperando confirmación del proveedor'),
        ('Confirmado', 2, 'fa-check-circle', '#3b82f6', 'Pedido confirmado por el proveedor'),
        ('En Preparación', 3, 'fa-cooking', '#8b5cf6', 'Productos siendo preparados'),
        ('En Camino', 4, 'fa-truck', '#10b981', 'Pedido en ruta de entrega'),
        ('Completado', 5, 'fa-check-double', '#22c55e', 'Pedido entregado exitosamente'),
        ('Cancelado', 6, 'fa-ban', '#ef4444', 'Pedido cancelado'),
    ]
    for nombre, orden, icono, color, desc in estados_data:
        Estadopedido.objects.get_or_create(
            estadonombre=nombre,
            defaults={'orden': orden, 'icono': icono, 'colorhex': color}
        )
    print(f"✅ {len(estados_data)} estados de pedido")
    
    # Departamentos y municipios (Nicaragua)
    deptos_munis = {
        'Managua': ['Managua', 'Ciudad Sandino', 'Tipitapa', 'San Rafael del Sur', 'Mateare'],
        'León': ['León', 'Nagarote', 'La Paz Centro', 'Telica', 'Quezalguaque'],
        'Granada': ['Granada', 'Diriomo', 'Nandaime', 'Diriá', 'Diriamba'],
        'Matagalpa': ['Matagalpa', 'Sébaco', 'San Ramón', 'Matiguás', 'Muy Muy'],
        'Estelí': ['Estelí', 'Condega', 'San Nicolás', 'Pueblo Nuevo', 'La Trinidad'],
        'Chinandega': ['Chinandega', 'El Viejo', 'Puerto Morazán', 'Somotillo', 'Villanueva'],
        'Masaya': ['Masaya', 'Nindirí', 'Tisma', 'Catarina', 'San Juan de Oriente'],
    }
    for depto, munis in deptos_munis.items():
        d, _ = Departamento.objects.get_or_create(nombredepartamento=depto)
        for muni in munis:
            Municipio.objects.get_or_create(nombremunicipio=muni, departamentoid=d)
    print(f"✅ {sum(len(m) for m in deptos_munis.values())} municipios en {len(deptos_munis)} departamentos")
    
    return rol_rest, rol_prov

def crear_restaurantes(rol_rest):
    print("\n" + "=" * 60)
    print("🍽️ 2. CREANDO RESTAURANTES")
    print("=" * 60)
    
    municipios = list(Municipio.objects.all())
    
    restaurantes_data = [
        {'razon': 'La Fonda S.A.', 'ruc': 'J0310000012345', 'telefono': '22551234', 'correo': 'reservas@lafonda.com', 'user': 'lafonda', 'descripcion': 'Comida tradicional nicaragüense'},
        {'razon': 'Comedor Doña Juanita', 'ruc': 'J0310000023456', 'telefono': '22555678', 'correo': 'info@donajuanita.com', 'user': 'donajuanita', 'descripcion': 'Comida casera y económica'},
        {'razon': 'Parrilla El Bosque', 'ruc': 'J0310000034567', 'telefono': '22559012', 'correo': 'contacto@parrillaelbosque.com', 'user': 'parrillaelbosque', 'descripcion': 'Especialidad en carnes a la parrilla'},
        {'razon': 'Sushi World', 'ruc': 'J0310000045678', 'telefono': '22553456', 'correo': 'pedidos@sushiworld.com', 'user': 'sushiworld', 'descripcion': 'Comida japonesa y sushi'},
        {'razon': 'Cafetería Central', 'ruc': 'J0310000056789', 'telefono': '22557890', 'correo': 'cafe@central.com', 'user': 'cafeteria', 'descripcion': 'Café y repostería artesanal'},
        {'razon': 'Pizzeria Napoli', 'ruc': 'J0310000067890', 'telefono': '22559876', 'correo': 'info@pizzanapoli.com', 'user': 'pizzanapoli', 'descripcion': 'Pizzas artesanales al horno'},
        {'razon': 'Mariscos El Galeón', 'ruc': 'J0310000078901', 'telefono': '22554321', 'correo': 'ventas@elgaleon.com', 'user': 'elgaleon', 'descripcion': 'Mariscos frescos del lago'},
        {'razon': 'Wok Oriental', 'ruc': 'J0310000089012', 'telefono': '22556789', 'correo': 'info@wokoriental.com', 'user': 'wokoriental', 'descripcion': 'Comida china y fusión asiática'},
        {'razon': 'Buffet El Palacio', 'ruc': 'J0310000090123', 'telefono': '22559876', 'correo': 'reservas@elpalacio.com', 'user': 'elpalacio', 'descripcion': 'Buffet internacional'},
    ]
    
    restaurantes_creados = []
    contrasena = 'restaurante123'
    
    for r in restaurantes_data:
        if Usuario.objects.filter(correoelectronico=r['correo']).exists():
            print(f"⚠️ {r['razon']} ya existe")
            continue
        
        usuario = Usuario.objects.create(
            rolid=rol_rest,
            nombreusuario=r['user'],
            correoelectronico=r['correo'],
            contrasena=make_password(contrasena),
            fecharegistro=timezone.now() - timedelta(days=random.randint(0, 365))
        )
        
        empresa = Empresa.objects.create(
            usuarioid=usuario,
            rolid=rol_rest,
            razonsocial=r['razon'],
            ruc=r['ruc'],
            telefono=r['telefono'],
            correoempresa=r['correo'],
            direccionfiscal=fake.address(),
            estado=True,
            logourl=f"https://picsum.photos/id/{random.randint(1,100)}/200/150"
        )
        
        # Crear entre 1 y 3 sucursales
        num_suc = random.randint(1, 3)
        for i in range(num_suc):
            municipio = random.choice(municipios)
            Sucursal.objects.create(
                empresaid=empresa,
                nombresucursal="Local Principal" if i == 0 else f"Sucursal {i+1}",
                municipioid=municipio,
                direccionexacta=fake.street_address(),
                telefonosucursal=fake.phone_number(),
                horarioatencion=f"{random.randint(7,10)}:00 - {random.randint(20,23)}:00",
                esbodega=False,
                estado="Activo",
                fecharegistro=timezone.now() - timedelta(days=random.randint(0, 180))
            )
        
        restaurantes_creados.append({'razon': r['razon'], 'user': r['user'], 'pass': contrasena})
        print(f"✅ {r['razon']} | usuario: {r['user']} | {num_suc} sucursal(es)")
    
    return restaurantes_creados

def crear_proveedores(rol_prov):
    print("\n" + "=" * 60)
    print("🏭 3. CREANDO PROVEEDORES")
    print("=" * 60)
    
    categorias = list(Categoria.objects.all())
    unidades = list(Unidadmedida.objects.all())
    municipios = list(Municipio.objects.all())
    
    proveedores_data = [
        {'razon': 'Carnes Selectas S.A.', 'ruc': 'J0310000012345', 'telefono': '22781234', 'correo': 'ventas@carnesselectas.com', 'user': 'carnes_selectas', 'categoria_principal': 'Carnes'},
        {'razon': 'Lácteos Estrella', 'ruc': 'J0310000023456', 'telefono': '22785678', 'correo': 'contacto@lacteosestrella.com', 'user': 'lacteos_estrella', 'categoria_principal': 'Lácteos'},
        {'razon': 'Distribuidora El Campo', 'ruc': 'J0310000034567', 'telefono': '22789012', 'correo': 'info@elcampo.com', 'user': 'el_campo', 'categoria_principal': 'Granos'},
        {'razon': 'Pesquera San Martín', 'ruc': 'J0310000045678', 'telefono': '22784567', 'correo': 'ventas@pesquerasm.com', 'user': 'pesquera_sm', 'categoria_principal': 'Carnes'},
        {'razon': 'Bebidas Tropicales S.A.', 'ruc': 'J0310000056789', 'telefono': '22789034', 'correo': 'info@bebidastropicales.com', 'user': 'bebidas_tropicales', 'categoria_principal': 'Bebidas'},
        {'razon': 'Panadería Moderna', 'ruc': 'J0310000067890', 'telefono': '22785690', 'correo': 'ventas@panaderiamoderna.com', 'user': 'panaderia_moderna', 'categoria_principal': 'Panadería'},
        {'razon': 'Frutas del Trópico', 'ruc': 'J0310000078901', 'telefono': '22784567', 'correo': 'ventas@frutasdeltropico.com', 'user': 'frutas_tropico', 'categoria_principal': 'Frutas'},
        {'razon': 'Especias y Sabores', 'ruc': 'J0310000089012', 'telefono': '22785678', 'correo': 'info@especiasysabores.com', 'user': 'especias_sabores', 'categoria_principal': 'Especias'},
    ]
    
    proveedores_creados = []
    contrasena = 'proveedor123'
    
    for p in proveedores_data:
        if Usuario.objects.filter(correoelectronico=p['correo']).exists():
            print(f"⚠️ {p['razon']} ya existe")
            continue
        
        usuario = Usuario.objects.create(
            rolid=rol_prov,
            nombreusuario=p['user'],
            correoelectronico=p['correo'],
            contrasena=make_password(contrasena),
            fecharegistro=timezone.now() - timedelta(days=random.randint(0, 365))
        )
        
        empresa = Empresa.objects.create(
            usuarioid=usuario,
            rolid=rol_prov,
            razonsocial=p['razon'],
            ruc=p['ruc'],
            telefono=p['telefono'],
            correoempresa=p['correo'],
            direccionfiscal=fake.address(),
            estado=True,
            logourl=f"https://picsum.photos/id/{random.randint(1,100)}/200/150"
        )
        
        # Sucursal principal (bodega)
        municipio = random.choice(municipios)
        bodega = Sucursal.objects.create(
            empresaid=empresa,
            nombresucursal="Bodega Central",
            municipioid=municipio,
            direccionexacta=fake.street_address(),
            telefonosucursal=p['telefono'],
            horarioatencion="8:00 - 17:00",
            esbodega=True,
            estado="Activo",
            fecharegistro=timezone.now() - timedelta(days=random.randint(0, 180))
        )
        
        # Sucursal de ventas (opcional)
        if random.choice([True, False]):
            municipio2 = random.choice([m for m in municipios if m.id != municipio.id] or municipios)
            Sucursal.objects.create(
                empresaid=empresa,
                nombresucursal="Centro de Ventas",
                municipioid=municipio2,
                direccionexacta=fake.street_address(),
                telefonosucursal=fake.phone_number(),
                horarioatencion="9:00 - 18:00",
                esbodega=False,
                estado="Activo",
                fecharegistro=timezone.now() - timedelta(days=random.randint(0, 180))
            )
        
        # Crear productos
        cat_principal = Categoria.objects.filter(nombrecategoria=p['categoria_principal']).first()
        if not cat_principal:
            cat_principal = random.choice(categorias)
        
        num_productos = random.randint(8, 15)
        lista_productos = []
        
        # Nombres de productos por categoría
        nombres_por_categoria = {
            'Carnes': ['Carne Molida', 'Pechuga de Pollo', 'Chuleta de Cerdo', 'Lomo de Res', 'Pescado Fresco', 'Pulpo', 'Camarones', 'Costilla de Cerdo', 'Pollo Entero'],
            'Lácteos': ['Leche Entera', 'Queso Fresco', 'Mantequilla', 'Yogur Natural', 'Crema', 'Queso Rayado', 'Leche Deslactosada', 'Yogur de Fresa'],
            'Granos': ['Arroz Precocido', 'Frijol Rojo', 'Frijol Negro', 'Maíz', 'Avena', 'Lentejas', 'Garbanzos', 'Quinoa'],
            'Verduras': ['Tomate', 'Cebolla', 'Lechuga', 'Zanahoria', 'Papa', 'Chile Dulce', 'Brócoli', 'Coliflor'],
            'Bebidas': ['Jugo de Naranja', 'Refresco Cola', 'Agua Purificada', 'Cerveza', 'Vino Tinto', 'Energizante', 'Agua Saborizada'],
            'Panadería': ['Pan Francés', 'Pan Integral', 'Pan Dulce', 'Baguette', 'Croissant', 'Pastel', 'Galletas', 'Pan de Molde'],
            'Frutas': ['Manzana', 'Naranja', 'Plátano', 'Sandía', 'Melón', 'Piña', 'Mango', 'Papaya', 'Fresa'],
            'Especias': ['Sal', 'Pimienta', 'Orégano', 'Comino', 'Paprika', 'Canela', 'Curry', 'Ajo en Polvo'],
        }
        
        for i in range(num_productos):
            if random.random() < 0.7:
                categoria = cat_principal
            else:
                categoria = random.choice([c for c in categorias if c.id != cat_principal.id] or categorias)
            
            unidad = random.choice(unidades)
            
            categoria_nombre = categoria.nombrecategoria
            if categoria_nombre in nombres_por_categoria:
                base_nombre = random.choice(nombres_por_categoria[categoria_nombre])
            else:
                base_nombre = fake.word().capitalize()
            
            nombre = f"{base_nombre} {random.choice(['Premium', 'Selecto', 'Fresco', 'Natural', 'Artesanal', 'Extra'])}"
            precio = round(random.uniform(30, 500), 2)
            
            producto = Producto.objects.create(
                empresaid=empresa,
                categoriaid=categoria,
                unidadmedidaid=unidad,
                nombreproducto=nombre,
                descripcion=fake.sentence(),
                precioventa=precio,
                cantidadminimapedido=random.randint(1, 10),
                esperecedero=categoria_nombre in ['Carnes', 'Lácteos', 'Verduras', 'Frutas'],
                diasvidautil=random.randint(3, 30) if categoria_nombre in ['Carnes', 'Lácteos', 'Verduras', 'Frutas'] else None,
                imagenurl=f"https://picsum.photos/id/{random.randint(1,100)}/200/150",
                eliminado=False
            )
            
            # Inventario
            stock = random.randint(50, 1000)
            Inventariobodega.objects.create(
                productoid=producto,
                sucursalid=bodega,
                stockdisponible=stock,
                stockminimo=random.randint(10, 50),
                ultimaactualizacion=timezone.now() - timedelta(days=random.randint(0, 30))
            )
            
            # Promociones (30% de productos)
            if random.random() < 0.3:
                descuento = random.randint(5, 25)
                fecha_inicio = timezone.now().date() - timedelta(days=random.randint(0, 10))
                fecha_fin = fecha_inicio + timedelta(days=random.randint(15, 60))
                Promocion.objects.create(
                    productoid=producto,
                    descripcion=f"Oferta especial {descuento}% de descuento",
                    cantidadminima=random.randint(2, 5),
                    porcentajedescuento=descuento,
                    fechainicio=fecha_inicio,
                    fechafin=fecha_fin
                )
            
            lista_productos.append(nombre)
        
        proveedores_creados.append({'razon': p['razon'], 'user': p['user'], 'pass': contrasena, 'productos': len(lista_productos)})
        print(f"✅ {p['razon']} | usuario: {p['user']} | {len(lista_productos)} productos")
    
    return proveedores_creados

def crear_pedidos(restaurantes, proveedores):
    print("\n" + "=" * 60)
    print("🚚 4. CREANDO PEDIDOS E HISTORIAL")
    print("=" * 60)
    
    estados = {e.estadonombre: e for e in Estadopedido.objects.all()}
    moneda = Moneda.objects.first()
    metodos = list(Metodopago.objects.all())
    
    total_pedidos = 0
    
    for restaurante in restaurantes:
        empresa_rest = Empresa.objects.filter(razonsocial=restaurante['razon']).first()
        if not empresa_rest:
            continue
        
        sucursal_entrega = Sucursal.objects.filter(empresaid=empresa_rest).first()
        if not sucursal_entrega:
            continue
        
        num_pedidos = random.randint(5, 15)
        
        for _ in range(num_pedidos):
            proveedor = random.choice(proveedores)
            empresa_prov = Empresa.objects.filter(razonsocial=proveedor['razon']).first()
            if not empresa_prov:
                continue
            
            sucursal_origen = Sucursal.objects.filter(empresaid=empresa_prov, esbodega=True).first()
            if not sucursal_origen:
                continue
            
            metodo = random.choice(metodos)
            
            # Seleccionar productos del proveedor
            productos_prov = list(Producto.objects.filter(empresaid=empresa_prov, eliminado=False))
            if not productos_prov:
                continue
            
            num_items = random.randint(1, 6)
            items = []
            subtotal = 0
            
            for __ in range(num_items):
                prod = random.choice(productos_prov)
                cantidad = random.randint(1, 20)
                
                # Verificar promoción vigente
                promocion = Promocion.objects.filter(
                    productoid=prod,
                    fechainicio__lte=timezone.now().date(),
                    fechafin__gte=timezone.now().date()
                ).first()
                
                precio_unit = float(prod.precioventa)
                descuento = 0
                
                if promocion and cantidad >= promocion.cantidadminima:
                    descuento = float(promocion.porcentajedescuento)
                    precio_unit = precio_unit * (1 - descuento / 100)
                
                subtotal += precio_unit * cantidad
                items.append({
                    'producto': prod,
                    'cantidad': cantidad,
                    'precio_unitario': precio_unit,
                    'descuento': descuento
                })
            
            impuesto = subtotal * 0.15
            total = subtotal + impuesto
            
            # Fecha del pedido (aleatoria entre hoy y 60 días atrás)
            fecha_pedido = timezone.now() - timedelta(days=random.randint(0, 60))
            
            pedido = Pedido.objects.create(
                restauranteid=empresa_rest,
                proveedorid=empresa_prov,
                sucursalorigenid=sucursal_origen,
                sucursalentregaid=sucursal_entrega,
                monedaid=moneda,
                metodopagoid=metodo,
                subtotal=round(subtotal, 2),
                impuesto=round(impuesto, 2),
                totalneto=round(total, 2),
                comentario=fake.sentence(),
                fechapedido=fecha_pedido
            )
            
            # Crear detalles
            for item in items:
                Detallepedido.objects.create(
                    pedidoid=pedido,
                    productoid=item['producto'],
                    cantidad=item['cantidad'],
                    preciounitario=item['precio_unitario'],
                    descuentoaplicado=item['descuento']
                )
            
            # Crear historial de estados (simulación realista)
            fecha_actual = fecha_pedido
            
            # Estado Pendiente
            Historialestadopedido.objects.create(
                pedidoid=pedido,
                estadoid=estados['Pendiente'],
                comentario="Pedido creado por el restaurante",
                fechacambio=fecha_actual
            )
            
            # Decidir estado final
            estado_final = random.choices(
                ['Completado', 'Cancelado', 'Confirmado'],
                weights=[0.6, 0.1, 0.3]
            )[0]
            
            if estado_final == 'Completado':
                fecha_actual += timedelta(hours=random.randint(1, 24))
                Historialestadopedido.objects.create(
                    pedidoid=pedido,
                    estadoid=estados['Confirmado'],
                    comentario="Pedido confirmado por el proveedor",
                    fechacambio=fecha_actual
                )
                
                fecha_actual += timedelta(hours=random.randint(2, 12))
                Historialestadopedido.objects.create(
                    pedidoid=pedido,
                    estadoid=estados['En Preparación'],
                    comentario="Productos en preparación",
                    fechacambio=fecha_actual
                )
                
                fecha_actual += timedelta(hours=random.randint(2, 8))
                Historialestadopedido.objects.create(
                    pedidoid=pedido,
                    estadoid=estados['En Camino'],
                    comentario="Pedido en ruta de entrega",
                    fechacambio=fecha_actual
                )
                
                fecha_actual += timedelta(hours=random.randint(1, 6))
                Historialestadopedido.objects.create(
                    pedidoid=pedido,
                    estadoid=estados['Completado'],
                    comentario="Pedido entregado exitosamente",
                    fechacambio=fecha_actual
                )
                
            elif estado_final == 'Cancelado':
                fecha_actual += timedelta(hours=random.randint(1, 48))
                Historialestadopedido.objects.create(
                    pedidoid=pedido,
                    estadoid=estados['Cancelado'],
                    comentario="Pedido cancelado",
                    fechacambio=fecha_actual
                )
                
            else:  # Confirmado pero no completado
                fecha_actual += timedelta(hours=random.randint(1, 24))
                Historialestadopedido.objects.create(
                    pedidoid=pedido,
                    estadoid=estados['Confirmado'],
                    comentario="Pedido confirmado, pendiente de preparación",
                    fechacambio=fecha_actual
                )
            
            total_pedidos += 1
    
    print(f"✅ {total_pedidos} pedidos creados con su historial")

def main():
    print("\n" + "=" * 60)
    print("🚀 INICIANDO LLENADO COMPLETO DE LA BASE DE DATOS")
    print("=" * 60 + "\n")
    
    # 1. Crear catálogos
    rol_rest, rol_prov = crear_catalogos()
    
    # 2. Crear restaurantes
    restaurantes = crear_restaurantes(rol_rest)
    
    # 3. Crear proveedores
    proveedores = crear_proveedores(rol_prov)
    
    # 4. Crear pedidos
    crear_pedidos(restaurantes, proveedores)
    
    # Resumen final
    print("\n" + "=" * 60)
    print("🎉 LLENADO COMPLETADO EXITOSAMENTE")
    print("=" * 60)
    print(f"\n📊 RESUMEN:")
    print(f"   🍽️ Restaurantes: {len(restaurantes)}")
    print(f"   🏭 Proveedores: {len(proveedores)}")
    
    print("\n🔐 CREDENCIALES DE ACCESO:")
    print("\n   RESTAURANTES (contraseña: restaurante123):")
    for r in restaurantes:
        print(f"      - {r['user']}")
    
    print("\n   PROVEEDORES (contraseña: proveedor123):")
    for p in proveedores:
        print(f"      - {p['user']}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()