"""Entidades del dominio. `Pedido` es además el *contexto* del patrón State."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")
METODOS_PAGO = ("Tarjeta de crédito", "Tarjeta de débito", "Yape", "Plin",
                "PagoEfectivo", "Transferencia")


def dinero(valor) -> Decimal:
    """Convierte a Decimal con 2 decimales (redondeo comercial)."""
    return Decimal(str(valor)).quantize(CENTIMO, rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------------
# Entidades simples (filas de la BD)
# ----------------------------------------------------------------------------
@dataclass(frozen=True)
class Variante:
    id_variante: int
    id_producto: int
    titulo: str
    talla: str
    color: str
    precio: Decimal
    stock: int
    id_vendedor: int | None = None

    def __str__(self) -> str:
        return f"{self.titulo} ({self.talla}, {self.color})"


@dataclass(frozen=True)
class Cupon:
    id_cupon: int
    codigo: str
    descuento_pct: int
    vence: date

    def vigente(self, en: date) -> bool:
        return en <= self.vence


@dataclass(frozen=True)
class Courier:
    id_courier: int
    nombre: str
    costo_base: Decimal


@dataclass
class ItemPedido:
    variante: Variante
    cantidad: int
    precio_unit: Decimal

    @property
    def importe(self) -> Decimal:
        return self.cantidad * self.precio_unit


# ----------------------------------------------------------------------------
# Pedido: contexto del patrón State
# ----------------------------------------------------------------------------
class Pedido:
    """Un pedido delega cada acción (pagar, enviar, entregar, cancelar) a su
    objeto de estado actual. El estado decide si la acción es válida y cuál
    es el siguiente estado. Se arma con `PedidoBuilder`."""

    def __init__(self, id_usuario: int, items: list[ItemPedido], fecha: datetime,
                 precio, cupon: Cupon | None = None, departamento: str | None = None,
                 estrategia_envio=None, id_pedido: int | None = None, estado=None):
        from .estados import Pendiente  # import local para evitar ciclo

        self.id_pedido = id_pedido
        self.id_usuario = id_usuario
        self.items = items
        self.fecha = fecha
        self.cupon = cupon
        self.departamento = departamento
        self.precio = precio                    # cadena de decoradores (descuentos.py)
        self.estrategia_envio = estrategia_envio  # Strategy (envios.py)
        self._estado = estado or Pendiente()
        self.historial: list[tuple[str | None, str]] = [(None, self._estado.nombre)]
        # se completan durante el ciclo de vida
        self.metodo_pago: str | None = None
        self.costo_envio: Decimal | None = None
        self.fecha_envio: datetime | None = None
        self.fecha_estimada: date | None = None
        self.fecha_entrega: datetime | None = None
        self.reembolsado = False

    # ----- montos ---------------------------------------------------------
    @property
    def subtotal(self) -> Decimal:
        return dinero(sum((i.importe for i in self.items), Decimal(0)))

    @property
    def total(self) -> Decimal:
        """Total de productos con todos los descuentos (lo que guarda pedidos.total)."""
        return dinero(self.precio.monto())

    @property
    def descuento(self) -> Decimal:
        return self.subtotal - self.total

    @property
    def unidades(self) -> int:
        return sum(i.cantidad for i in self.items)

    @property
    def entrega_tardia(self) -> bool | None:
        if self.fecha_entrega is None or self.fecha_estimada is None:
            return None
        return self.fecha_entrega.date() > self.fecha_estimada

    # ----- State: el pedido delega en su estado ----------------------------
    @property
    def estado(self) -> str:
        return self._estado.nombre

    def acciones_posibles(self) -> list[str]:
        return self._estado.acciones_permitidas()

    def pagar(self, metodo: str) -> None:
        self._estado.pagar(self, metodo)

    def enviar(self, estrategia=None, fecha: datetime | None = None) -> None:
        self._estado.enviar(self, estrategia, fecha)

    def entregar(self, fecha: datetime | None = None) -> None:
        self._estado.entregar(self, fecha)

    def cancelar(self) -> None:
        self._estado.cancelar(self)

    def _cambiar_estado(self, nuevo) -> None:
        """Solo lo llaman las clases de estado."""
        self.historial.append((self._estado.nombre, nuevo.nombre))
        self._estado = nuevo

    # ----- presentación ---------------------------------------------------
    def resumen(self) -> str:
        id_txt = self.id_pedido if self.id_pedido is not None else "(sin guardar)"
        lineas = [f"Pedido {id_txt} — usuario {self.id_usuario} — estado: {self.estado}"]
        for it in self.items:
            lineas.append(f"  {it.cantidad} x {it.variante}  @ S/ {it.precio_unit:,.2f}"
                          f"  = S/ {it.importe:,.2f}")
        for etiqueta, monto in self.precio.lineas():
            lineas.append(f"  {etiqueta:<38} S/ {dinero(monto):>10,.2f}")
        lineas.append(f"  {'TOTAL PRODUCTOS':<38} S/ {self.total:>10,.2f}")
        if self.costo_envio is not None:
            lineas.append(f"  {'Envío (' + self.estrategia_envio.nombre + ')':<38}"
                          f" S/ {self.costo_envio:>10,.2f}")
        return "\n".join(lineas)

    def __repr__(self) -> str:
        return f"<Pedido {self.id_pedido} {self.estado} S/ {self.total}>"
