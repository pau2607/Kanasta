"""Acceso a la base de datos MySQL `marketplace`.

Toda la lectura/escritura en la BD vive aquí; las clases de los patrones
(Builder, Decorator, Strategy, State) no saben nada de SQL.
"""
from __future__ import annotations

from datetime import datetime
from itertools import groupby

import mysql.connector

from .builder import PedidoBuilder
from .envios import estrategia_para
from .modelos import Courier, Cupon, Pedido, Variante

SQL_VARIANTE = """
    SELECT v.id_variante, v.id_producto, p.titulo, v.talla, v.color,
           p.precio, v.stock, p.id_vendedor
    FROM variantes v JOIN productos p ON p.id_producto = v.id_producto
"""


def _variante(f: dict) -> Variante:
    return Variante(f["id_variante"], f["id_producto"], f["titulo"], f["talla"],
                    f["color"], f["precio"], f["stock"], f["id_vendedor"])


def _cupon(f: dict) -> Cupon | None:
    if f.get("id_cupon") is None:
        return None
    return Cupon(f["id_cupon"], f["codigo"], f["descuento_pct"], f["vence"])


class Repositorio:
    def __init__(self, config: dict):
        self.cnx = mysql.connector.connect(**config, autocommit=False)

    # permite usar: with Repositorio(DB_CONFIG) as repo: ...
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cerrar()

    def cerrar(self):
        if self.cnx.is_connected():
            self.cnx.close()

    def _todos(self, sql: str, params=()) -> list[dict]:
        cur = self.cnx.cursor(dictionary=True)
        cur.execute(sql, params)
        filas = cur.fetchall()
        cur.close()
        self.cnx.commit()   # cierra la transacción de lectura (ve datos frescos)
        return filas

    def _uno(self, sql: str, params=()) -> dict | None:
        filas = self._todos(sql, params)
        return filas[0] if filas else None

    # ------------------------------------------------------------------ lecturas
    def variante(self, id_variante: int) -> Variante:
        f = self._uno(SQL_VARIANTE + " WHERE v.id_variante = %s", (id_variante,))
        if f is None:
            raise LookupError(f"No existe la variante {id_variante}")
        return _variante(f)

    def variantes_con_stock(self, id_vendedor: int, minimo: int = 5, limite: int = 5) -> list[Variante]:
        filas = self._todos(SQL_VARIANTE + """
            WHERE p.id_vendedor = %s AND v.stock >= %s
            ORDER BY v.id_variante LIMIT %s""", (id_vendedor, minimo, limite))
        return [_variante(f) for f in filas]

    def cupon(self, codigo: str) -> Cupon | None:
        return _cupon(self._uno("SELECT * FROM cupones WHERE codigo = %s", (codigo,)) or {})

    def cupones_vigentes(self, en: datetime) -> list[Cupon]:
        filas = self._todos("""SELECT * FROM cupones WHERE vence >= %s
                               ORDER BY descuento_pct DESC, vence""", (en.date(),))
        return [_cupon(f) for f in filas]

    def couriers(self) -> list[Courier]:
        return [Courier(f["id_courier"], f["nombre"], f["costo_base"])
                for f in self._todos("SELECT * FROM couriers ORDER BY id_courier")]

    def departamento_de(self, id_usuario: int) -> str:
        f = self._uno("""SELECT d.departamento FROM usuarios u
                         JOIN distritos d ON d.id_distrito = u.id_distrito
                         WHERE u.id_usuario = %s""", (id_usuario,))
        if f is None:
            raise LookupError(f"No existe el usuario {id_usuario}")
        return f["departamento"]

    def stock_de(self, id_variante: int) -> int:
        return self._uno("SELECT stock FROM variantes WHERE id_variante = %s",
                         (id_variante,))["stock"]

    # ------------------------------------------------- pedidos (lectura masiva)
    SQL_PEDIDOS = """
        SELECT p.id_pedido, p.id_usuario, p.fecha, p.estado, p.total AS total_bd,
               di.departamento,
               c.id_cupon, c.codigo, c.descuento_pct, c.vence,
               e.id_courier, co.nombre AS courier, co.costo_base,
               e.fecha_envio, e.fecha_entrega, e.fecha_estimada, e.costo_envio,
               d.id_variante, d.cantidad, d.precio_unit,
               v.id_producto, v.talla, v.color, v.stock, pr.titulo, pr.precio, pr.id_vendedor
        FROM pedidos p
        JOIN usuarios u        ON u.id_usuario   = p.id_usuario
        JOIN distritos di      ON di.id_distrito = u.id_distrito
        JOIN pedido_detalle d  ON d.id_pedido    = p.id_pedido
        JOIN variantes v       ON v.id_variante  = d.id_variante
        JOIN productos pr      ON pr.id_producto = v.id_producto
        LEFT JOIN cupones c    ON c.id_cupon     = p.id_cupon
        LEFT JOIN envios e     ON e.id_pedido    = p.id_pedido
        LEFT JOIN couriers co  ON co.id_courier  = e.id_courier
    """

    @staticmethod
    def _armar_pedido(filas: list[dict]) -> Pedido:
        """Reconstruye un Pedido (con su estado y envío) usando el Builder.

        Ojo: la BD solo guarda el cupón. Si el pedido tuvo descuentos extra
        (volumen, medio de pago, monto fijo), `pedido.total` se recalcula solo
        con el cupón; el total real cobrado está en `pedido.total_bd`.
        """
        f0 = filas[0]
        b = (PedidoBuilder(f0["id_usuario"], f0["departamento"])
             .desde_bd(f0["id_pedido"], f0["estado"])
             .en_fecha(f0["fecha"])
             .con_cupon(_cupon(f0)))
        for f in filas:
            b.agregar(_variante(f), f["cantidad"], f["precio_unit"])
        if f0["id_courier"] is not None:
            b.enviar_con(estrategia_para(Courier(f0["id_courier"], f0["courier"], f0["costo_base"])))
        pedido = b.build()
        pedido.total_bd = f0["total_bd"]            # lo guardado, para comparar
        pedido.costo_envio = f0["costo_envio"]
        pedido.fecha_envio = f0["fecha_envio"]
        pedido.fecha_entrega = f0["fecha_entrega"]
        pedido.fecha_estimada = f0["fecha_estimada"]
        return pedido

    def pedido(self, id_pedido: int) -> Pedido:
        filas = self._todos(self.SQL_PEDIDOS + " WHERE p.id_pedido = %s", (id_pedido,))
        if not filas:
            raise LookupError(f"No existe el pedido {id_pedido} (o no tiene ítems)")
        return self._armar_pedido(filas)

    def iterar_pedidos(self, donde: str = "", params=(), lote: int = 5000):
        """GENERADOR: entrega los pedidos de la BD uno por uno.

        Lee las filas de a `lote` con fetchmany, así nunca tiene los 247 mil
        ítems en memoria a la vez. Mientras se recorre, no uses el mismo
        repositorio para otras consultas.
        """
        cur = self.cnx.cursor(dictionary=True, buffered=False)
        sql = self.SQL_PEDIDOS + (f" WHERE {donde}" if donde else "") + " ORDER BY p.id_pedido"
        cur.execute(sql, params)

        def filas():
            while bloque := cur.fetchmany(lote):
                yield from bloque

        try:
            for _, grupo in groupby(filas(), key=lambda f: f["id_pedido"]):
                yield self._armar_pedido(list(grupo))
        finally:
            # si se dejó de recorrer a medias (break, close), descartar lo no leído
            if self.cnx.unread_result:
                self.cnx.consume_results()
            cur.close()
            self.cnx.commit()

    # ---------------------------------------------------------------- escrituras
    def guardar_pedido(self, pedido: Pedido) -> int:
        """INSERT del pedido (pendiente) y sus ítems en una sola transacción."""
        cur = self.cnx.cursor()
        try:
            cur.execute("""INSERT INTO pedidos (id_usuario, id_cupon, fecha, estado, total)
                           VALUES (%s, %s, %s, 'pendiente', %s)""",
                        (pedido.id_usuario, pedido.cupon.id_cupon if pedido.cupon else None,
                         pedido.fecha.replace(microsecond=0), pedido.total))
            id_pedido = cur.lastrowid
            cur.executemany("""INSERT INTO pedido_detalle (id_pedido, id_variante, cantidad, precio_unit)
                               VALUES (%s, %s, %s, %s)""",
                            [(id_pedido, i.variante.id_variante, i.cantidad, i.precio_unit)
                             for i in pedido.items])
            self.cnx.commit()
            return id_pedido
        except Exception:
            self.cnx.rollback()
            raise
        finally:
            cur.close()

    def confirmar_pedido(self, id_pedido: int, metodo: str) -> dict:
        """Llama al procedimiento almacenado sp_confirmar_pedido (transacción en MySQL)."""
        cur = self.cnx.cursor(dictionary=True)
        try:
            cur.callproc("sp_confirmar_pedido", (id_pedido, metodo))
            resultado = {}
            for res in cur.stored_results():
                resultado = res.fetchone() or resultado
            self.cnx.commit()
            return resultado
        except Exception:
            self.cnx.rollback()
            raise
        finally:
            cur.close()

    def _cambiar_estado(self, cur, id_pedido: int, de: str, a: str):
        # WHERE con el estado esperado: si otro proceso lo cambió, no se pisa
        cur.execute("UPDATE pedidos SET estado = %s WHERE id_pedido = %s AND estado = %s",
                    (a, id_pedido, de))
        if cur.rowcount != 1:
            raise RuntimeError(f"El pedido {id_pedido} ya no está '{de}' en la BD")

    def registrar_envio(self, pedido: Pedido) -> None:
        cur = self.cnx.cursor()
        try:
            cur.execute("""INSERT INTO envios (id_pedido, id_courier, fecha_envio,
                                               fecha_estimada, costo_envio)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (pedido.id_pedido, pedido.estrategia_envio.courier.id_courier,
                         pedido.fecha_envio, pedido.fecha_estimada, pedido.costo_envio))
            self._cambiar_estado(cur, pedido.id_pedido, "pagado", "enviado")
            self.cnx.commit()
        except Exception:
            self.cnx.rollback()
            raise
        finally:
            cur.close()

    def registrar_entrega(self, pedido: Pedido) -> None:
        cur = self.cnx.cursor()
        try:
            cur.execute("UPDATE envios SET fecha_entrega = %s WHERE id_pedido = %s",
                        (pedido.fecha_entrega, pedido.id_pedido))
            self._cambiar_estado(cur, pedido.id_pedido, "enviado", "entregado")
            self.cnx.commit()
        except Exception:
            self.cnx.rollback()
            raise
        finally:
            cur.close()

    def cancelar_pedido(self, pedido: Pedido, estado_anterior: str) -> None:
        """Cancela; si ya estaba pagado devuelve el stock y marca el pago como reembolsado."""
        cur = self.cnx.cursor()
        try:
            if estado_anterior == "pagado":
                cur.execute("""UPDATE variantes v JOIN pedido_detalle d ON d.id_variante = v.id_variante
                               SET v.stock = v.stock + d.cantidad WHERE d.id_pedido = %s""",
                            (pedido.id_pedido,))
                cur.execute("""UPDATE pagos SET estado = 'reembolsado'
                               WHERE id_pedido = %s AND estado = 'aprobado'""", (pedido.id_pedido,))
            else:
                cur.execute("""UPDATE pagos SET estado = 'rechazado'
                               WHERE id_pedido = %s AND estado = 'pendiente'""", (pedido.id_pedido,))
            self._cambiar_estado(cur, pedido.id_pedido, estado_anterior, "cancelado")
            self.cnx.commit()
        except Exception:
            self.cnx.rollback()
            raise
        finally:
            cur.close()
