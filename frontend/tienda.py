"""Datos de la tienda (vista cliente) y escrituras propias de la app."""
from __future__ import annotations

from datetime import datetime

import mysql.connector
import pandas as pd
import streamlit as st

from config import DB_CONFIG

from .datos import a_float, leer


def ejecutar(sql: str, params: tuple = ()) -> int:
    """INSERT/UPDATE/DELETE con commit. Devuelve lastrowid (o filas afectadas)."""
    cnx = mysql.connector.connect(**DB_CONFIG)
    try:
        cur = cnx.cursor()
        cur.execute(sql, params)
        cnx.commit()
        return cur.lastrowid or cur.rowcount
    finally:
        cnx.close()


# ------------------------------------------------------------- ampliación del modelo
SQL_CHECKOUT = """
CREATE TABLE IF NOT EXISTS checkout (
  id_pedido     INT          NOT NULL,
  id_courier    INT          NOT NULL,
  costo_envio   DECIMAL(8,2) NOT NULL,
  metodo_pago   VARCHAR(30)  NOT NULL,
  descuentos    VARCHAR(255) NULL,
  creado        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_pedido),
  CONSTRAINT fk_checkout_pedido  FOREIGN KEY (id_pedido)  REFERENCES pedidos (id_pedido) ON DELETE CASCADE,
  CONSTRAINT fk_checkout_courier FOREIGN KEY (id_courier) REFERENCES couriers (id_courier)
) ENGINE = InnoDB"""


@st.cache_resource(show_spinner=False)
def asegurar_tablas() -> bool:
    """La app guarda el courier y método elegidos en el checkout (la tabla pedidos no los tiene)."""
    ejecutar(SQL_CHECKOUT)
    return True


def guardar_checkout(id_pedido: int, id_courier: int, costo: float, metodo: str, descuentos: str):
    ejecutar("""INSERT INTO checkout (id_pedido, id_courier, costo_envio, metodo_pago, descuentos)
                VALUES (%s, %s, %s, %s, %s)""", (id_pedido, id_courier, costo, metodo, descuentos[:255]))


def checkout_de(id_pedido: int) -> dict | None:
    df = leer("""SELECT k.*, c.nombre AS courier FROM checkout k JOIN couriers c USING (id_courier)
                 WHERE k.id_pedido = %s""", (id_pedido,))
    return None if df.empty else df.iloc[0].to_dict()


def registrar_pago_pendiente(id_pedido: int, metodo: str, monto: float):
    """PagoEfectivo: se genera un código y el pago queda pendiente hasta que el cliente paga."""
    ejecutar("INSERT INTO pagos (id_pedido, metodo, monto, estado) VALUES (%s, %s, %s, 'pendiente')",
             (id_pedido, metodo, monto))


# ------------------------------------------------------------- catálogo
@st.cache_data(ttl=600, show_spinner="Cargando la tienda…")
def catalogo() -> pd.DataFrame:
    df = leer("""
        SELECT p.id_producto, p.titulo, p.precio, p.id_vendedor, ve.razon_social, ve.reputacion,
               p.id_categoria, h.nombre AS hoja, s.nombre AS sub, r.nombre AS raiz,
               COALESCE(vt.vendidos, 0) AS vendidos, rs.rating, COALESCE(rs.n, 0) AS n_resenas,
               st.stock_total, st.variantes
        FROM productos p
        JOIN vendedores ve ON ve.id_vendedor = p.id_vendedor
        JOIN categorias h ON h.id_categoria = p.id_categoria
        JOIN categorias s ON s.id_categoria = h.id_padre
        JOIN categorias r ON r.id_categoria = s.id_padre
        JOIN (SELECT id_producto, SUM(stock) AS stock_total, COUNT(*) AS variantes
              FROM variantes GROUP BY id_producto) st ON st.id_producto = p.id_producto
        LEFT JOIN (SELECT v.id_producto, SUM(d.cantidad) AS vendidos
                   FROM pedido_detalle d JOIN variantes v USING (id_variante)
                   JOIN pedidos pe USING (id_pedido) WHERE pe.estado <> 'cancelado'
                   GROUP BY v.id_producto) vt ON vt.id_producto = p.id_producto
        LEFT JOIN (SELECT id_producto, AVG(estrellas) AS rating, COUNT(*) AS n
                   FROM resenas GROUP BY id_producto) rs ON rs.id_producto = p.id_producto""")
    df = a_float(df, "precio", "reputacion")
    df["rating"] = df["rating"].astype(float)
    for c in ("vendidos", "n_resenas", "stock_total", "variantes"):
        df[c] = df[c].astype(int)
    return df


def variantes_producto(id_producto: int) -> pd.DataFrame:
    return leer("""SELECT id_variante, talla, color, stock FROM variantes
                   WHERE id_producto = %s ORDER BY talla, color""", (id_producto,))


def resenas_producto(id_producto: int, n: int = 4) -> pd.DataFrame:
    return leer("""SELECT r.estrellas, r.comentario, r.fecha, u.nombre FROM resenas r
                   JOIN usuarios u USING (id_usuario)
                   WHERE r.id_producto = %s AND r.comentario IS NOT NULL
                   ORDER BY r.fecha DESC LIMIT %s""", (id_producto, n))


def preguntas_producto(id_producto: int, n: int = 3) -> pd.DataFrame:
    return leer("""SELECT texto, respuesta, fecha FROM preguntas WHERE id_producto = %s
                   ORDER BY fecha DESC LIMIT %s""", (id_producto, n))


def crear_pregunta(id_producto: int, id_usuario: int, texto: str):
    ejecutar("INSERT INTO preguntas (id_producto, id_usuario, texto, fecha) VALUES (%s, %s, %s, %s)",
             (id_producto, id_usuario, texto[:255], datetime.now().replace(microsecond=0)))


@st.cache_data(ttl=600, show_spinner=False)
def tiendas_top(n: int = 6) -> pd.DataFrame:
    c = catalogo()
    t = (c.groupby(["id_vendedor", "razon_social", "reputacion"])
         .agg(vendidos=("vendidos", "sum"), productos=("id_producto", "size"),
              raiz=("raiz", lambda s: s.mode().iat[0]))
         .reset_index().sort_values("vendidos", ascending=False))
    return t.head(n)


# ------------------------------------------------------------- cliente
def cliente(id_usuario: int) -> dict | None:
    df = leer("""SELECT u.id_usuario, u.nombre, u.email, u.fecha_registro, d.nombre AS distrito,
                        d.provincia, d.departamento
                 FROM usuarios u JOIN distritos d USING (id_distrito) WHERE u.id_usuario = %s""",
              (id_usuario,))
    return None if df.empty else df.iloc[0].to_dict()


def pedidos_cliente(id_usuario: int) -> pd.DataFrame:
    return a_float(leer("""
        SELECT p.id_pedido, p.fecha, p.estado, p.total, COUNT(*) AS items, SUM(d.cantidad) AS unidades,
               MIN(v.id_producto) AS id_producto_1
        FROM pedidos p JOIN pedido_detalle d USING (id_pedido) JOIN variantes v USING (id_variante)
        WHERE p.id_usuario = %s
        GROUP BY p.id_pedido, p.fecha, p.estado, p.total
        ORDER BY p.fecha DESC, p.id_pedido DESC""", (id_usuario,)), "total")


def items_pedido(id_pedido: int) -> pd.DataFrame:
    return a_float(leer("""
        SELECT d.id_variante, v.id_producto, p.titulo, v.talla, v.color, d.cantidad, d.precio_unit,
               h.nombre AS hoja, r.nombre AS raiz
        FROM pedido_detalle d JOIN variantes v USING (id_variante) JOIN productos p USING (id_producto)
        JOIN categorias h ON h.id_categoria = p.id_categoria
        JOIN categorias s ON s.id_categoria = h.id_padre JOIN categorias r ON r.id_categoria = s.id_padre
        WHERE d.id_pedido = %s""", (id_pedido,)), "precio_unit")


def compras_validas(id_usuario: int) -> int:
    return int(leer("""SELECT COUNT(*) AS n FROM pedidos WHERE id_usuario = %s
                       AND estado IN ('pagado', 'enviado', 'entregado')""", (id_usuario,))["n"].iat[0])


def productos_comprados(id_usuario: int) -> list[int]:
    df = leer("""SELECT DISTINCT v.id_producto FROM pedidos p JOIN pedido_detalle d USING (id_pedido)
                 JOIN variantes v USING (id_variante)
                 WHERE p.id_usuario = %s AND p.estado <> 'cancelado'""", (id_usuario,))
    return df["id_producto"].tolist()


def resenados_por(id_usuario: int) -> set[int]:
    return set(leer("SELECT id_producto FROM resenas WHERE id_usuario = %s", (id_usuario,))["id_producto"])


def crear_resena(id_producto: int, id_usuario: int, estrellas: int, comentario: str | None):
    ejecutar("""INSERT INTO resenas (id_producto, id_usuario, estrellas, comentario, fecha)
                VALUES (%s, %s, %s, %s, %s)""",
             (id_producto, id_usuario, estrellas, (comentario or None) and comentario[:255],
              datetime.now().date()))


# ------------------------------------------------------------- favoritos
def favoritos_de(id_usuario: int) -> set[int]:
    return set(leer("SELECT id_producto FROM favoritos WHERE id_usuario = %s", (id_usuario,))["id_producto"])


def alternar_favorito(id_usuario: int, id_producto: int) -> bool:
    """Agrega o quita de favoritos. Devuelve True si quedó como favorito."""
    if id_producto in favoritos_de(id_usuario):
        ejecutar("DELETE FROM favoritos WHERE id_usuario = %s AND id_producto = %s", (id_usuario, id_producto))
        return False
    ejecutar("INSERT INTO favoritos (id_usuario, id_producto, fecha) VALUES (%s, %s, %s)",
             (id_usuario, id_producto, datetime.now().date()))
    return True


# ------------------------------------------------------------- admin
def conteo_estados() -> dict[str, int]:
    df = leer("SELECT estado, COUNT(*) AS n FROM pedidos GROUP BY estado")
    return dict(zip(df["estado"], df["n"].astype(int)))


def pedidos_por_estado(estado: str, n: int = 100) -> pd.DataFrame:
    return a_float(leer("""
        SELECT p.id_pedido, p.fecha, u.nombre AS cliente, d.departamento AS destino, p.total,
               c.nombre AS courier_elegido, k.metodo_pago
        FROM pedidos p JOIN usuarios u USING (id_usuario) JOIN distritos d USING (id_distrito)
        LEFT JOIN checkout k ON k.id_pedido = p.id_pedido
        LEFT JOIN couriers c ON c.id_courier = k.id_courier
        WHERE p.estado = %s ORDER BY p.fecha DESC, p.id_pedido DESC LIMIT %s""", (estado, n)), "total")


def ventas_hoy() -> dict:
    """Actividad creada desde la app (pedidos posteriores al fin del dataset)."""
    df = leer("""SELECT COUNT(*) AS pedidos, COALESCE(SUM(total), 0) AS ventas FROM pedidos
                 WHERE fecha > '2026-09-30 23:59:59' AND estado IN ('pagado','enviado','entregado')""")
    return {"pedidos": int(df["pedidos"].iat[0]), "ventas": float(df["ventas"].iat[0])}
