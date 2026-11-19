"""Patrón Builder — armar un pedido paso a paso.

Un pedido tiene muchas partes opcionales (varios ítems, cupón, descuentos
extra, courier, fecha). En vez de un constructor con 10 parámetros, el
builder las va recibiendo una por una y valida todo junto en `build()`:

    pedido = (PedidoBuilder(id_usuario=2474, departamento="Lima")
              .agregar(variante_a, 2)
              .agregar(variante_b)
              .con_cupon(cupon)
              .con_descuento_volumen()
              .enviar_con(estrategia)
              .build())
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from .descuentos import (DescuentoCupon, DescuentoMedioPago, DescuentoMontoFijo,
                         DescuentoPorVolumen, PrecioBase)
from .estados import estado_desde_nombre
from .modelos import Cupon, ItemPedido, Pedido, Variante, dinero


class ErrorPedido(ValueError):
    pass


class PedidoBuilder:
    def __init__(self, id_usuario: int, departamento: str | None = None):
        self._id_usuario = id_usuario
        self._departamento = departamento
        self._items: dict[int, ItemPedido] = {}   # clave: id_variante
        self._cupon: Cupon | None = None
        self._extras = []                          # funciones que agregan decoradores
        self._estrategia = None
        self._fecha: datetime | None = None
        self._id_pedido = None
        self._estado = None
        self._es_nuevo = True        # False = pedido histórico leído de la BD

    # ----- pasos ------------------------------------------------------------
    def agregar(self, variante: Variante, cantidad: int = 1, precio_unit=None) -> "PedidoBuilder":
        if cantidad <= 0:
            raise ErrorPedido("La cantidad debe ser mayor que 0")
        precio = dinero(precio_unit if precio_unit is not None else variante.precio)
        if variante.id_variante in self._items:           # misma variante: se suma
            self._items[variante.id_variante].cantidad += cantidad
        else:
            self._items[variante.id_variante] = ItemPedido(variante, cantidad, precio)
        return self

    def con_cupon(self, cupon: Cupon | None) -> "PedidoBuilder":
        self._cupon = cupon
        return self

    def con_descuento_volumen(self, min_unidades: int = 6, pct=5) -> "PedidoBuilder":
        self._extras.append(lambda p, b: DescuentoPorVolumen(p, b._unidades(), min_unidades, pct))
        return self

    def con_descuento_medio_pago(self, metodo: str, pct) -> "PedidoBuilder":
        self._extras.append(lambda p, b: DescuentoMedioPago(p, metodo, pct))
        return self

    def con_descuento_fijo(self, soles, motivo: str = "Descuento fijo") -> "PedidoBuilder":
        self._extras.append(lambda p, b: DescuentoMontoFijo(p, soles, motivo))
        return self

    def enviar_con(self, estrategia) -> "PedidoBuilder":
        self._estrategia = estrategia
        return self

    def en_fecha(self, fecha: datetime) -> "PedidoBuilder":
        self._fecha = fecha
        return self

    # Para reconstruir pedidos históricos leídos de la BD
    def desde_bd(self, id_pedido: int, estado: str) -> "PedidoBuilder":
        self._id_pedido = id_pedido
        self._estado = estado
        self._es_nuevo = False   # ni el stock ni los cupones de hoy aplican a compras pasadas
        return self

    # ----- resultado ---------------------------------------------------------
    def _unidades(self) -> int:
        return sum(i.cantidad for i in self._items.values())

    def build(self) -> Pedido:
        fecha = self._fecha or datetime.now()
        items = list(self._items.values())

        if not items:
            raise ErrorPedido("El pedido no tiene ítems")
        if self._es_nuevo:
            sin_stock = [f"{i.variante} (pide {i.cantidad}, hay {i.variante.stock})"
                         for i in items if i.cantidad > i.variante.stock]
            if sin_stock:
                raise ErrorPedido("Stock insuficiente: " + "; ".join(sin_stock))
        if self._es_nuevo and self._cupon and not self._cupon.vigente(fecha.date()):
            raise ErrorPedido(f"El cupón {self._cupon.codigo} venció el {self._cupon.vence}")
        if self._estrategia and self._departamento and not self._estrategia.atiende(self._departamento):
            raise ErrorPedido(f"{self._estrategia.nombre} no reparte en {self._departamento}")

        # Decorator: precio base → cupón → demás descuentos, en el orden agregado
        precio = PrecioBase(items)
        if self._cupon:
            precio = DescuentoCupon(precio, self._cupon)
        for agregar_descuento in self._extras:
            precio = agregar_descuento(precio, self)

        return Pedido(
            id_usuario=self._id_usuario, items=items, fecha=fecha, precio=precio,
            cupon=self._cupon, departamento=self._departamento,
            estrategia_envio=self._estrategia, id_pedido=self._id_pedido,
            estado=estado_desde_nombre(self._estado) if self._estado else None)
