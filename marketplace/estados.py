"""Patrón State — ciclo de vida de un pedido.

    pendiente ──pagar──▶ pagado ──enviar──▶ enviado ──entregar──▶ entregado
        │                  │
        └──cancelar──▶ cancelado ◀──cancelar (con reembolso)

Cada estado es una clase. Solo implementa las acciones válidas en ese
momento; cualquier otra lanza `TransicionInvalida`. Así el `Pedido` no
necesita una cadena de if/elif sobre el estado.
"""
from __future__ import annotations

from abc import ABC
from datetime import datetime

from .modelos import METODOS_PAGO

ACCIONES = ("pagar", "enviar", "entregar", "cancelar")


class TransicionInvalida(Exception):
    pass


class EstadoPedido(ABC):
    nombre = ""
    final = False

    # Por defecto, ninguna acción está permitida.
    def pagar(self, pedido, metodo: str) -> None:
        self._invalida("pagar")

    def enviar(self, pedido, estrategia=None, fecha: datetime | None = None) -> None:
        self._invalida("enviar")

    def entregar(self, pedido, fecha: datetime | None = None) -> None:
        self._invalida("entregar")

    def cancelar(self, pedido) -> None:
        self._invalida("cancelar")

    def acciones_permitidas(self) -> list[str]:
        """Acciones que esta clase sobrescribe (las que sí puede hacer)."""
        return [a for a in ACCIONES
                if getattr(type(self), a) is not getattr(EstadoPedido, a)]

    def _invalida(self, accion: str):
        raise TransicionInvalida(
            f"No se puede {accion} un pedido en estado '{self.nombre}'. "
            f"Acciones posibles: {', '.join(self.acciones_permitidas()) or 'ninguna'}")

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class Pendiente(EstadoPedido):
    nombre = "pendiente"

    def pagar(self, pedido, metodo: str) -> None:
        if metodo not in METODOS_PAGO:
            raise ValueError(f"Método de pago no válido: {metodo}")
        pedido.metodo_pago = metodo
        pedido._cambiar_estado(Pagado())

    def cancelar(self, pedido) -> None:
        pedido._cambiar_estado(Cancelado())


class Pagado(EstadoPedido):
    nombre = "pagado"

    def enviar(self, pedido, estrategia=None, fecha: datetime | None = None) -> None:
        # aquí State usa a Strategy: el costo depende del courier elegido
        estrategia = estrategia or pedido.estrategia_envio
        if estrategia is None:
            raise ValueError("Falta elegir el courier (estrategia de envío)")
        pedido.costo_envio = estrategia.cotizar(pedido.departamento)
        pedido.fecha_estimada = estrategia.fecha_estimada(pedido.fecha, pedido.departamento)
        pedido.estrategia_envio = estrategia
        pedido.fecha_envio = (fecha or datetime.now()).replace(microsecond=0)
        pedido._cambiar_estado(Enviado())

    def cancelar(self, pedido) -> None:
        pedido.reembolsado = True          # ya se cobró: hay que devolver el dinero
        pedido._cambiar_estado(Cancelado())


class Enviado(EstadoPedido):
    nombre = "enviado"

    def entregar(self, pedido, fecha: datetime | None = None) -> None:
        fecha = (fecha or datetime.now()).replace(microsecond=0)
        if pedido.fecha_envio and fecha < pedido.fecha_envio:
            raise ValueError("La entrega no puede ser anterior al envío")
        pedido.fecha_entrega = fecha
        pedido._cambiar_estado(Entregado())


class Entregado(EstadoPedido):
    nombre = "entregado"
    final = True


class Cancelado(EstadoPedido):
    nombre = "cancelado"
    final = True


ESTADOS = {c.nombre: c for c in (Pendiente, Pagado, Enviado, Entregado, Cancelado)}


def estado_desde_nombre(nombre: str) -> EstadoPedido:
    """Para reconstruir un pedido leído de la BD (columna pedidos.estado)."""
    return ESTADOS[nombre]()
