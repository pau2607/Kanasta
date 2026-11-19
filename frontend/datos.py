"""Acceso a datos para la app: conexión por sesión y consultas en caché."""
from __future__ import annotations

import mysql.connector
import pandas as pd
import streamlit as st

from config import DB_CONFIG
from marketplace.envios import estrategia_para
from marketplace.modelos import Courier
from marketplace.repositorio import Repositorio
from marketplace.servicio import ServicioPedidos

CORTE = "2026-09-30 23:59:59"          # fin del dataset (los pedidos de la app son posteriores)
VALIDOS = ("pagado", "enviado", "entregado")


# ------------------------------------------------------------------ conexión
def repo() -> Repositorio:
    """Un Repositorio (conexión MySQL) por pestaña del navegador."""
    r = st.session_state.get("_repo")
    if r is None or not r.cnx.is_connected():
        r = Repositorio(DB_CONFIG)
        st.session_state["_repo"] = r
    return r


def servicio() -> ServicioPedidos:
    return ServicioPedidos(repo())


def probar_conexion() -> str | None:
    """Devuelve None si conecta, o el mensaje de error."""
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cnx.close()
        return None
    except Exception as e:  # noqa: BLE001
        return str(e)


def leer(sql: str, params: tuple = ()) -> pd.DataFrame:
    """SELECT → DataFrame con una conexión propia (sirve para funciones en caché)."""
    cnx = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = cnx.cursor()
        cur.execute(sql, params)
        df = pd.DataFrame(cur.fetchall(), columns=cur.column_names)
        cur.close()
        return df
    finally:
        cnx.close()


def a_float(df: pd.DataFrame, *cols: str) -> pd.DataFrame:
    for c in cols:
        df[c] = df[c].astype(float)
    return df


# ------------------------------------------------------------- en vivo (sin caché)
def pedidos_recientes(n: int = 12) -> pd.DataFrame:
    return a_float(leer("""
        SELECT p.id_pedido, p.fecha, u.nombre AS cliente, d.departamento, p.estado, p.total
        FROM pedidos p JOIN usuarios u USING (id_usuario) JOIN distritos d USING (id_distrito)
        ORDER BY p.id_pedido DESC LIMIT %s""", (n,)), "total")


def cliente(id_usuario: int) -> dict | None:
    df = leer("""SELECT u.id_usuario, u.nombre, u.email, d.nombre AS distrito, d.departamento
                 FROM usuarios u JOIN distritos d USING (id_distrito) WHERE u.id_usuario = %s""",
              (id_usuario,))
    return None if df.empty else df.iloc[0].to_dict()


def variantes_de(id_vendedor: int) -> pd.DataFrame:
    return a_float(leer("""
        SELECT v.id_variante, p.id_producto, p.titulo, v.talla, v.color, p.precio, v.stock,
               c.nombre AS categoria
        FROM variantes v JOIN productos p USING (id_producto)
        JOIN categorias c ON c.id_categoria = p.id_categoria
        WHERE p.id_vendedor = %s ORDER BY p.titulo, v.talla, v.color""", (id_vendedor,)), "precio")


def variantes_producto(id_producto: int) -> pd.DataFrame:
    return leer("SELECT id_variante, talla, color, stock FROM variantes WHERE id_producto = %s "
                "ORDER BY stock DESC", (id_producto,))


def pagos_de(id_pedido: int) -> pd.DataFrame:
    return a_float(leer("SELECT id_pago, metodo, monto, estado FROM pagos WHERE id_pedido = %s "
                        "ORDER BY id_pago", (id_pedido,)), "monto")


def stock_items(id_pedido: int) -> pd.DataFrame:
    return leer("""SELECT d.id_variante, p.titulo, v.talla, v.color, d.cantidad, v.stock AS stock_actual
                   FROM pedido_detalle d JOIN variantes v USING (id_variante)
                   JOIN productos p USING (id_producto) WHERE d.id_pedido = %s""", (id_pedido,))


# ---------------------------------------------------------------- catálogos
@st.cache_data(ttl=3600, show_spinner=False)
def vendedores_con_productos() -> pd.DataFrame:
    return leer("""SELECT ve.id_vendedor, ve.razon_social, COUNT(*) AS productos
                   FROM vendedores ve JOIN productos p USING (id_vendedor)
                   GROUP BY ve.id_vendedor, ve.razon_social ORDER BY productos DESC""")


@st.cache_data(ttl=3600, show_spinner=False)
def couriers() -> list[Courier]:
    df = leer("SELECT * FROM couriers ORDER BY id_courier")
    return [Courier(int(r.id_courier), r.nombre, r.costo_base) for r in df.itertuples()]


def estrategias():
    return [estrategia_para(c) for c in couriers()]


@st.cache_data(ttl=3600, show_spinner=False)
def arbol_categorias() -> pd.DataFrame:
    """WITH RECURSIVE: nivel, ruta y ventas acumuladas (incluye descendientes)."""
    return a_float(leer(f"""
        WITH RECURSIVE arbol AS (
            SELECT id_categoria, id_padre, nombre, 1 AS nivel, CAST(nombre AS CHAR(300)) AS ruta
            FROM categorias WHERE id_padre IS NULL
            UNION ALL
            SELECT c.id_categoria, c.id_padre, c.nombre, a.nivel + 1, CONCAT(a.ruta, ' > ', c.nombre)
            FROM categorias c JOIN arbol a ON c.id_padre = a.id_categoria
        ),
        ancestros AS (
            SELECT id_categoria AS anc, id_categoria AS des FROM categorias
            UNION ALL
            SELECT a.anc, c.id_categoria FROM ancestros a JOIN categorias c ON c.id_padre = a.des
        ),
        ventas_hoja AS (
            SELECT pr.id_categoria, SUM(d.cantidad * d.precio_unit) AS ventas, SUM(d.cantidad) AS unidades
            FROM pedido_detalle d JOIN pedidos p USING (id_pedido)
            JOIN variantes v USING (id_variante) JOIN productos pr USING (id_producto)
            WHERE p.estado IN ('pagado', 'enviado', 'entregado') AND p.fecha <= '{CORTE}'
            GROUP BY pr.id_categoria
        )
        SELECT ar.id_categoria, ar.id_padre, ar.nombre, ar.nivel, ar.ruta,
               COALESCE(SUM(vh.ventas), 0) AS ventas, COALESCE(SUM(vh.unidades), 0) AS unidades
        FROM arbol ar
        JOIN ancestros an ON an.anc = ar.id_categoria
        LEFT JOIN ventas_hoja vh ON vh.id_categoria = an.des
        GROUP BY ar.id_categoria, ar.id_padre, ar.nombre, ar.nivel, ar.ruta
        ORDER BY ar.ruta"""), "ventas", "unidades")


def stock_critico() -> pd.DataFrame:
    """Variantes con 0-3 unidades y su demanda en los últimos 90 días (en vivo)."""
    df = leer(f"""
        WITH demanda AS (
            SELECT d.id_variante, SUM(d.cantidad) AS vendidas_90d
            FROM pedido_detalle d JOIN pedidos p USING (id_pedido)
            WHERE p.estado <> 'cancelado'
              AND p.fecha >= TIMESTAMP('{CORTE}') - INTERVAL 90 DAY
            GROUP BY d.id_variante)
        SELECT v.id_variante, pr.titulo, v.talla, v.color, v.stock,
               COALESCE(de.vendidas_90d, 0) AS vendidas_90d,
               ve.razon_social AS vendedor, c.nombre AS categoria
        FROM variantes v JOIN productos pr USING (id_producto)
        JOIN vendedores ve ON ve.id_vendedor = pr.id_vendedor
        JOIN categorias c ON c.id_categoria = pr.id_categoria
        LEFT JOIN demanda de ON de.id_variante = v.id_variante
        WHERE v.stock <= 3
        ORDER BY vendidas_90d DESC, v.stock""")
    df["vendidas_90d"] = df["vendidas_90d"].astype(int)
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def niveles_stock() -> pd.DataFrame:
    return leer("""SELECT CASE WHEN stock = 0 THEN 'Agotado (0)' WHEN stock <= 3 THEN 'Crítico (1-3)'
                               WHEN stock <= 10 THEN 'Bajo (4-10)' ELSE 'Normal (>10)' END AS nivel,
                          COUNT(*) AS variantes, MIN(stock) AS orden
                   FROM variantes GROUP BY nivel ORDER BY orden""")
