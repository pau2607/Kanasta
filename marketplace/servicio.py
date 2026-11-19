"""Servicio que une el dominio (patrones) con la base de datos.

Cada operación primero ejecuta la transición en el objeto (State valida si
es posible) y luego la guarda en MySQL. Si MySQL falla, el objeto vuelve a
su estado anterior para que memoria y BD no queden distintas.
"""
from __future__ import annotations

from .builder import PedidoBuilder
from .envios import comparar, estrategia_para
from .modelos import Pedido
from .repositorio import Repositorio


class ServicioPedidos:
    def __init__(self, repo: Repositorio):
        self.repo = repo

    def nuevo_pedido(self, id_usuario: int) -> PedidoBuilder:
        """Devuelve un Builder ya con el departamento de destino del usuario."""
        return PedidoBuilder(id_usuario, self.repo.departamento_de(id_usuario))

    def estrategias(self):
        return [estrategia_para(c) for c in self.repo.couriers()]

    def opciones_envio(self, pedido: Pedido):
        return comparar(self.estrategias(), pedido.departamento)

    # ----------------------------------------------------------- operaciones
    def registrar(self, pedido: Pedido) -> Pedido:
        if pedido.id_pedido is not None:
            raise ValueError(f"El pedido {pedido.id_pedido} ya está guardado")
        pedido.id_pedido = self.repo.guardar_pedido(pedido)
        return pedido

    def pagar(self, pedido: Pedido, metodo: str) -> Pedido:
        return self._transicion(pedido, lambda: pedido.pagar(metodo),
                                lambda: self.repo.confirmar_pedido(pedido.id_pedido, metodo))

    def despachar(self, pedido: Pedido, estrategia=None) -> Pedido:
        return self._transicion(pedido, lambda: pedido.enviar(estrategia),
                                lambda: self.repo.registrar_envio(pedido))

    def entregar(self, pedido: Pedido, fecha=None) -> Pedido:
        return self._transicion(pedido, lambda: pedido.entregar(fecha),
                                lambda: self.repo.registrar_entrega(pedido))

    def cancelar(self, pedido: Pedido) -> Pedido:
        anterior = pedido.estado
        return self._transicion(pedido, pedido.cancelar,
                                lambda: self.repo.cancelar_pedido(pedido, anterior))

    @staticmethod
    def _transicion(pedido: Pedido, en_objeto, en_bd) -> Pedido:
        if pedido.id_pedido is None:
            raise ValueError("Primero registra el pedido con registrar()")
        respaldo = dict(vars(pedido))
        respaldo["historial"] = list(pedido.historial)
        en_objeto()                 # si la transición no es válida, falla aquí sin tocar la BD
        try:
            en_bd()
        except Exception:
            vars(pedido).clear()
            vars(pedido).update(respaldo)   # deshacer el cambio en memoria
            raise
        return pedido
