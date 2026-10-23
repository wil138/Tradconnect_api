# Copia como configurar-entorno.ps1, llena los valores y ejecuta:
# . ./configurar-entorno.ps1
# python manage.py runserver
$env:MONGODB_URI = "" # mongodb://localhost:27017 o URI de Atlas
$env:MONGODB_DATABASE = "tradconnect"
$env:SQLSERVER_HOST = "" # Servidor o instancia SQL Server
$env:SQLSERVER_DATABASE = "TradConnect"
$env:SQLSERVER_USER = "" # Vac?o para autenticaci?n Windows
$env:SQLSERVER_PASSWORD = ""
$env:SQLSERVER_DRIVER = "ODBC Driver 17 for SQL Server"
