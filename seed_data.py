#!/usr/bin/env python
# seed_db.py - Poblar base de datos con datos realistas (Restaurantes y Proveedores)
# Ejecutar: python seed_db.py

import sys
import os
import random
from datetime import datetime, timedelta

# Añadir el directorio actual al path para poder importar la configuración de Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar el módulo de settings de Django
# Si tu proyecto se llama diferente, cambia 'TradConnect_Api.settings' por 'tu_proyecto.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TradConnect_Api.settings')

# Intentar importar Django y configurarlo
try:
    import django
    django.setup()
except ImportError as e:
    print(f"Error: No se puede importar Django. Asegúrate de que esté instalado en tu entorno virtual.")
    print(f"Detalle: {e}")
    sys.exit(1)

# Importar modelos (ajusta el nombre de la app si es diferente)
try:
    from tradconnect.models import (
        Rol, Categoria, Unidadmedida, Metodopago, Moneda, Estadopedido,
        Departamento, Municipio, Usuario, Empresa, Sucursal, Producto,
        Inventariobodega, Promocion, Pedido, Detallepedido, Historialestadopedido
    )
except ImportError as e:
    print(f"Error: No se puede importar 'tradconnect.models'. Verifica el nombre de tu app.")
    print(f"Detalle: {e}")
    sys.exit(1)

from django.contrib.auth.hashers import make_password
from django.utils import timezone

# Para datos falsos (necesitas instalar Faker: pip install Faker)
try:
    from faker import Faker
    fake = Faker('es_ES')
except ImportError:
    print("Advertencia: Faker no está instalado. Se usarán datos estáticos.")
    fake = None

# =========================================================
# CONFIGURACIÓN
# =========================================================
def run():
    print("🌱 Conectando a la base de datos...")
    
    # Limpiar datos existentes (opcional, descomentar si quieres reiniciar)
    # print("🧹 Limpiando datos existentes...")
    # Historialestadopedido.objects.all().delete()
    # Detallepedido.objects.all().delete()
    # Pedido.objects.all().delete()
    # Promocion.objects.all().delete()
    # Inventariobodega.objects.all().delete()
    # Producto.objects.all().delete()
    # Sucursal.objects.all().delete()
    # Empresa.objects.all().delete()
    # Usuario.objects.all().delete()
    # ... etc. No lo haremos por defecto.

    # 1. Catálogos base
    print("📦 Creando catálogos...")
    rol_rest, _ = Rol.objects.get_or_create(nombrerol='Restaurante')
    rol_prov, _ = Rol.objects.get_or_create(nombrerol='Proveedor')

    categorias_data = [
        ('Carnes', 'Productos cárnicos', 'fa-drumstick-bite', '#ef4444'),
        ('Lácteos', 'Lácteos y derivados', 'fa-cheese', '#f59e0b'),
        ('Verduras', 'Verduras frescas', 'fa-carrot', '#10b981'),
        ('Granos', 'Granos básicos', 'fa-wheat-alt', '#8b5cf6'),
        ('Bebidas', 'Bebidas y jugos', 'fa-wine-bottle', '#3b82f6'),
        ('Panadería', 'Pan y repostería', 'fa-bread-slice', '#d97706'),
    ]
    for nombre, desc, icono, color in categorias_data:
        Categoria.objects.get_or_create(nombrecategoria=nombre, defaults={'descripcion': desc, 'icono': icono, 'colorhex': color})

    unidades_data = [
        ('Kilogramo', 'kg', 'fa-weight-hanging'),
        ('Litro', 'L', 'fa-fill-drip'),
        ('Unidad', 'und', 'fa-cube'),
        ('Bolsa', 'bolsa', 'fa-bag-shopping'),
        ('Caja', 'caja', 'fa-box'),
        ('Docena', 'doc', 'fa-egg'),
    ]
    for nombre, abrev, icono in unidades_data:
        Unidadmedida.objects.get_or_create(nombreunidad=nombre, defaults={'abreviatura': abrev, 'icono': icono})

    metodos_data = [
        ('Transferencia bancaria', 'fa-building-columns'),
        ('Efectivo', 'fa-money-bill'),
        ('Tarjeta de crédito', 'fa-credit-card'),
        ('Contra entrega', 'fa-truck-fast'),
    ]
    for nombre, icono in metodos_data:
        Metodopago.objects.get_or_create(nombremetodo=nombre, defaults={'icono': icono, 'descripcion': f'Pago mediante {nombre.lower()}'})

    Moneda.objects.get_or_create(nombremoneda='Córdoba', defaults={'simbolo': 'C$', 'icono': 'fa-money-bill'})
    Moneda.objects.get_or_create(nombremoneda='Dólar', defaults={'simbolo': '$', 'icono': 'fa-dollar-sign'})

    estados_data = [
        ('Pendiente', 1, 'fa-clock', '#f59e0b'),
        ('Confirmado', 2, 'fa-check-circle', '#3b82f6'),
        ('En Preparación', 3, 'fa-cooking', '#8b5cf6'),
        ('En Camino', 4, 'fa-truck', '#10b981'),
        ('Completado', 5, 'fa-check-double', '#22c55e'),
        ('Cancelado', 6, 'fa-ban', '#ef4444'),
    ]
    for nombre, orden, icono, color in estados_data:
        Estadopedido.objects.get_or_create(estadonombre=nombre, defaults={'orden': orden, 'icono': icono, 'colorhex': color})

    # Departamentos y municipios (Nicaragua)
    deptos_munis = {
        'Managua': ['Managua', 'Ciudad Sandino', 'Tipitapa'],
        'León': ['León', 'Nagarote', 'La Paz Centro'],
        'Granada': ['Granada', 'Diriomo', 'Nandaime'],
        'Matagalpa': ['Matagalpa', 'Sébaco', 'San Ramón'],
        'Estelí': ['Estelí', 'Condega', 'San Nicolás'],
    }
    for depto, munis in deptos_munis.items():
        d, _ = Departamento.objects.get_or_create(nombredepartamento=depto)
        for muni in munis:
            Municipio.objects.get_or_create(nombremunicipio=muni, departamentoid=d)

    # 2. Empresas (Proveedores y Restaurantes)
    print("🏢 Creando empresas...")
    proveedores_data = [
        {'razon': 'Carnes Selectas S.A.', 'ruc': 'J0310000012345', 'telefono': '22781234', 'correo': 'ventas@carnesselectas.com', 'user': 'carnes_selectas', 'pass': 'proveedor123'},
        {'razon': 'Lácteos Estrella', 'ruc': 'J0310000023456', 'telefono': '22785678', 'correo': 'contacto@lacteosestrella.com', 'user': 'lacteos_estrella', 'pass': 'proveedor123'},
        {'razon': 'Distribuidora El Campo', 'ruc': 'J0310000034567', 'telefono': '22789012', 'correo': 'info@elcampo.com', 'user': 'el_campo', 'pass': 'proveedor123'},
    ]
    proveedores = []
    for p in proveedores_data:
        usuario, _ = Usuario.objects.get_or_create(
            correoelectronico=p['correo'],
            defaults={
                'rolid': rol_prov,
                'nombreusuario': p['user'],
                'contrasena': make_password(p['pass']),
                'fecharegistro': timezone.now()
            }
        )
        empresa, _ = Empresa.objects.get_or_create(
            usuarioid=usuario,
            defaults={
                'rolid': rol_prov,
                'razonsocial': p['razon'],
                'ruc': p['ruc'],
                'telefono': p['telefono'],
                'correoempresa': p['correo'],
                'direccionfiscal': fake.address() if fake else 'Dirección ficticia',
                'estado': True,
                'logourl': None
            }
        )
        proveedores.append(empresa)

    restaurantes_data = [
        {'razon': 'La Fonda S.A.', 'ruc': 'J0310000045678', 'telefono': '22551234', 'correo': 'reservas@lafonda.com', 'user': 'lafonda', 'pass': 'restaurante123'},
        {'razon': 'Comedor Doña Juanita', 'ruc': 'J0310000056789', 'telefono': '22555678', 'correo': 'info@donajuanita.com', 'user': 'donajuanita', 'pass': 'restaurante123'},
        {'razon': 'Parrilla El Bosque', 'ruc': 'J0310000067890', 'telefono': '22559012', 'correo': 'contacto@parrillaelbosque.com', 'user': 'parrillaelbosque', 'pass': 'restaurante123'},
        {'razon': 'Sushi World', 'ruc': 'J0310000078901', 'telefono': '22553456', 'correo': 'pedidos@sushiworld.com', 'user': 'sushiworld', 'pass': 'restaurante123'},
        {'razon': 'Cafetería Central', 'ruc': 'J0310000089012', 'telefono': '22557890', 'correo': 'cafe@central.com', 'user': 'cafeteria', 'pass': 'restaurante123'},
    ]
    restaurantes = []
    for r in restaurantes_data:
        usuario, _ = Usuario.objects.get_or_create(
            correoelectronico=r['correo'],
            defaults={
                'rolid': rol_rest,
                'nombreusuario': r['user'],
                'contrasena': make_password(r['pass']),
                'fecharegistro': timezone.now()
            }
        )
        empresa, _ = Empresa.objects.get_or_create(
            usuarioid=usuario,
            defaults={
                'rolid': rol_rest,
                'razonsocial': r['razon'],
                'ruc': r['ruc'],
                'telefono': r['telefono'],
                'correoempresa': r['correo'],
                'direccionfiscal': fake.address() if fake else 'Dirección ficticia',
                'estado': True,
                'logourl': None
            }
        )
        restaurantes.append(empresa)

    # 3. Sucursales
    print("🏬 Creando sucursales...")
    for empresa in proveedores + restaurantes:
        num_suc = random.randint(1, 3)
        municipios = list(Municipio.objects.all())
        for i in range(num_suc):
            municipio = random.choice(municipios)
            es_bodega = (empresa.rolid.nombrerol == 'Proveedor' and i == 0)
            nombre = "Bodega Central" if es_bodega else f"Sucursal {i+1}" if i>0 else "Local Principal"
            Sucursal.objects.get_or_create(
                empresaid=empresa,
                nombresucursal=nombre,
                municipioid=municipio,
                defaults={
                    'direccionexacta': fake.street_address() if fake else 'Calle ficticia',
                    'telefonosucursal': fake.phone_number() if fake else '00000000',
                    'horarioatencion': "8:00 - 17:00",
                    'esbodega': es_bodega,
                    'estado': "Activo",
                    'fecharegistro': timezone.now()
                }
            )

    # 4. Productos por proveedor
    print("📦 Creando productos...")
    categorias = list(Categoria.objects.all())
    unidades = list(Unidadmedida.objects.all())
    productos_por_proveedor = {}
    for proveedor in proveedores:
        num_prod = random.randint(8, 15)
        prod_list = []
        for _ in range(num_prod):
            cat = random.choice(categorias)
            unidad = random.choice(unidades)
            nombre = f"{fake.unique.word().capitalize()} {random.choice(['Premium', 'Fresco', 'Natural', 'Selecto'])}" if fake else f"Producto {_}"
            precio = round(random.uniform(50, 500), 2)
            prod, _ = Producto.objects.get_or_create(
                empresaid=proveedor,
                nombreproducto=nombre,
                defaults={
                    'categoriaid': cat,
                    'unidadmedidaid': unidad,
                    'descripcion': fake.sentence() if fake else 'Descripción genérica',
                    'precioventa': precio,
                    'cantidadminimapedido': random.randint(1, 10),
                    'esperecedero': random.choice([True, False]),
                    'diasvidautil': random.randint(1, 30) if random.choice([True, False]) else None,
                    'imagenurl': f"https://picsum.photos/id/{random.randint(1,100)}/200/150",
                    'eliminado': False
                }
            )
            prod_list.append(prod)
        productos_por_proveedor[proveedor.id] = prod_list

    # 5. Inventario y promociones
    print("📊 Creando inventario y promociones...")
    for proveedor in proveedores:
        bodegas = Sucursal.objects.filter(empresaid=proveedor, esbodega=True)
        if not bodegas:
            continue
        bodega = bodegas.first()
        productos = productos_por_proveedor.get(proveedor.id, [])
        for prod in productos:
            stock = random.randint(10, 500)
            Inventariobodega.objects.get_or_create(
                productoid=prod,
                sucursalid=bodega,
                defaults={
                    'stockdisponible': stock,
                    'stockminimo': random.randint(5, 20),
                    'ultimaactualizacion': timezone.now()
                }
            )
            if random.random() < 0.2:  # 20% de productos con promoción
                descuento = random.randint(5, 20)
                fecha_inicio = timezone.now().date()
                fecha_fin = fecha_inicio + timedelta(days=random.randint(15, 60))
                Promocion.objects.get_or_create(
                    productoid=prod,
                    fechainicio=fecha_inicio,
                    fechafin=fecha_fin,
                    defaults={
                        'descripcion': f"Oferta especial {descuento}%",
                        'cantidadminima': random.randint(2, 5),
                        'porcentajedescuento': descuento,
                    }
                )

    # 6. Pedidos con historial
    print("🚚 Creando pedidos e historial...")
    estados = {e.estadonombre: e for e in Estadopedido.objects.all()}
    moneda = Moneda.objects.first()
    metodos = list(Metodopago.objects.all())

    for restaurante in restaurantes:
        sucursal_entrega = Sucursal.objects.filter(empresaid=restaurante).first()
        if not sucursal_entrega:
            continue
        num_pedidos = random.randint(5, 20)
        for _ in range(num_pedidos):
            proveedor = random.choice(proveedores)
            sucursal_origen = Sucursal.objects.filter(empresaid=proveedor, esbodega=True).first()
            if not sucursal_origen:
                continue
            metodo = random.choice(metodos)
            productos_prov = productos_por_proveedor.get(proveedor.id, [])
            if not productos_prov:
                continue
            num_items = random.randint(1, 5)
            items = []
            subtotal = 0
            for __ in range(num_items):
                prod = random.choice(productos_prov)
                cantidad = random.randint(1, 20)
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

            pedido = Pedido.objects.create(
                restauranteid=restaurante,
                proveedorid=proveedor,
                sucursalorigenid=sucursal_origen,
                sucursalentregaid=sucursal_entrega,
                monedaid=moneda,
                metodopagoid=metodo,
                subtotal=subtotal,
                impuesto=impuesto,
                totalneto=total,
                comentario=fake.sentence() if fake else 'Sin comentarios',
                fechapedido=timezone.now() - timedelta(days=random.randint(0, 60))
            )
            for item in items:
                Detallepedido.objects.create(
                    pedidoid=pedido,
                    productoid=item['producto'],
                    cantidad=item['cantidad'],
                    preciounitario=item['precio_unitario'],
                    descuentoaplicado=item['descuento']
                )
            # Historial de estados
            fecha_pedido = pedido.fechapedido
            # Elegir estado final con mayor probabilidad de Completado
            estado_final = random.choices(
                [estados['Completado'], estados['Cancelado'], estados['Pendiente'], estados['Confirmado']],
                weights=[0.6, 0.1, 0.1, 0.2]
            )[0]
            secuencia = [estados['Pendiente']]
            if estado_final.estadonombre == 'Completado':
                for nombre in ['Confirmado', 'En Preparación', 'En Camino']:
                    secuencia.append(estados[nombre])
                secuencia.append(estados['Completado'])
            elif estado_final.estadonombre == 'Confirmado':
                secuencia.append(estados['Confirmado'])
            elif estado_final.estadonombre == 'Cancelado':
                if random.choice([True, False]):
                    secuencia.append(estados['Confirmado'])
                secuencia.append(estados['Cancelado'])
            current_date = fecha_pedido
            for idx, estado in enumerate(secuencia):
                if idx > 0:
                    current_date += timedelta(hours=random.randint(1, 48))
                Historialestadopedido.objects.create(
                    pedidoid=pedido,
                    estadoid=estado,
                    comentario=f"Pedido {estado.estadonombre.lower()}",
                    fechacambio=current_date
                )

    print("\n🎉 Seeding completado exitosamente.")
    print("\n🔐 Usuarios de prueba (contraseñas en texto plano para login):")
    print("   Proveedores:")
    for p in proveedores_data:
        print(f"      {p['user']} / {p['pass']}")
    print("   Restaurantes:")
    for r in restaurantes_data:
        print(f"      {r['user']} / {r['pass']}")
    print("\nNota: Las contraseñas se almacenan cifradas con el algoritmo de Django (PBKDF2).")

if __name__ == '__main__':
    run()