# Configuracion local. Copia como configurar-entorno.ps1 si quieres sobreescribirla:
# . ./configurar-entorno.ps1
# python manage.py runserver
$env:MONGODB_URI = "mongodb://localhost:27017"
$env:MONGODB_DATABASE = "tradconnect_db"
$env:SQLSERVER_HOST = ".\WIL"
$env:SQLSERVER_DATABASE = "TradConnect"
$env:SQLSERVER_PORT = ""
$env:SQLSERVER_USER = "" # Vacio para autenticacion de Windows
$env:SQLSERVER_PASSWORD = ""
$env:SQLSERVER_DRIVER = "ODBC Driver 18 for SQL Server"

# En Azure App Service, selecciona el perfil cloud y configura estos valores
# como Application settings/secretos (no descomentes ni guardes secretos aqui):
# $env:DATABASE_PROFILE = "cloud"
# $env:CLOUD_SQLSERVER_CONNECTION_STRING = "<cadena SQL Server privada>"
# $env:CLOUD_SQLSERVER_DRIVER = "ODBC Driver 18 for SQL Server"
# $env:CLOUD_MONGODB_URI = "<URI MongoDB privada>"
# $env:CLOUD_MONGODB_DATABASE = "<nombre de base MongoDB>"
