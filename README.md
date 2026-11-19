# Kanasta — Marketplace multivendedor (Programación Avanzada, UP)

Tienda y panel de administración en Streamlit sobre MySQL, con los patrones Builder, Strategy,
Decorator y State, consultas SQL (WITH RECURSIVE, procedimiento con transacción) y análisis con Pandas.

- App: `app.py` (Streamlit 1.67, Python 3.12)
- Base de datos: MySQL 8 con la base `marketplace` (scripts 01, 02 y 03 del proyecto)
- Conexión: variables `MKT_HOST`, `MKT_PORT`, `MKT_USER`, `MKT_PASSWORD`, `MKT_DATABASE`
  (en Streamlit Cloud van en *Secrets*; ver `.streamlit/secrets.toml.ejemplo`)
