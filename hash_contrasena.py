import os
import django

# 1. Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings') # <-- Cambia 'tu_proyecto' por el nombre real de tu carpeta de configuración
django.setup()

from django.contrib.auth.hashers import make_password, identify_hasher
from TradConnect.models import Usuario # <-- Cambia 'tu_aplicacion' por el nombre de tu app de Django

def hashear_contrasenas_existentes():
    print("=== Iniciando proceso de hashing de contraseñas ===")
    
    # Obtener todos los usuarios
    usuarios = Usuario.objects.all()
    contador_actualizados = 0

    for usuario in usuarios:
        pass_actual = usuario.contrasena

        # Verificamos si la contraseña ya está hasheada.
        # Si Django no reconoce el formato como un hash válido, lanzará una excepción ValueError.
        try:
            identify_hasher(pass_actual)
            # Si pasa aquí, significa que ya es un hash (ej: pbkdf2_sha256$...), así que lo ignoramos
            print(f"[-] Usuario {usuario.nombreusuario}: Ya tiene la contraseña hasheada. Omitiendo.")
        except ValueError:
            # Si entra aquí, significa que está en texto plano. ¡Procedemos a hashear!
            print(f"[+] Usuario {usuario.nombreusuario}: Contraseña en texto plano detectada. Hasheando...")
            
            # Aplicamos el algoritmo de Django
            usuario.contrasena = make_password(pass_actual)
            usuario.save(update_fields=['contrasena'])
            
            contador_actualizados += 1

    print("\n=== Proceso completado ===")
    print(f"Total de usuarios actualizados con éxito: {contador_actualizados}")

if __name__ == '__main__':
    hashear_contrasenas_existentes()