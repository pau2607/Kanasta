"""Datos de conexión a MySQL.

En la nube (Streamlit Community Cloud) se leen de los *Secrets* de la app, que Streamlit
expone como variables de entorno: MKT_HOST, MKT_PORT, MKT_USER, MKT_PASSWORD y MKT_DATABASE.
En tu computadora puedes crear .streamlit/secrets.toml con esas mismas claves (no se sube a GitHub).
"""
import os
import time

# Las fechas de pedidos, envíos y entregas se registran en hora de Perú (el servidor está en UTC).
os.environ.setdefault("TZ", "America/Lima")
if hasattr(time, "tzset"):
    time.tzset()

DB_CONFIG = {
    "host": os.getenv("MKT_HOST", "localhost"),
    "port": int(os.getenv("MKT_PORT", "3306")),
    "user": os.getenv("MKT_USER", "root"),
    "password": os.getenv("MKT_PASSWORD", ""),
    "database": os.getenv("MKT_DATABASE", "marketplace"),
    "connection_timeout": 15,
}
