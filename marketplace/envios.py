"""Patrón Strategy — cálculo del costo de envío según el courier.

Reglas obtenidas de los datos (tabla envios, 98 076 filas):
  * costo = costo_base del courier + S/ 6 si el destino es provincia
    (los datos traen además una variación aleatoria de -2 a +4 soles).
  * Chazki y 99minutos solo reparten en Lima/Callao (son express, ~1 día).
  * Fecha prometida: 3 días en Lima; 6 en provincia + días extra en zonas
    alejadas (Loreto y Madre de Dios hasta 10).

Cada familia de reglas es una estrategia intercambiable. El `Pedido` guarda
la estrategia elegida y la usa al pasar a "enviado".
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from decimal import Decimal

LIMA_METROPOLITANA = {"Lima", "Callao"}
RECARGO_PROVINCIA = Decimal("6.00")
DIAS_EXTRA = {"Loreto": 4, "Madre de Dios": 4, "Ucayali": 3, "Amazonas": 3,
              "San Martín": 2, "Puno": 2, "Apurímac": 2, "Tumbes": 1, "Tacna": 1,
              "Cusco": 1, "Ayacucho": 1, "Huánuco": 1}
SOLO_LIMA = {"Chazki", "99minutos"}


class DestinoNoAtendido(Exception):
    pass


def es_lima(departamento: str) -> bool:
    return departamento in LIMA_METROPOLITANA


def dias_prometidos(departamento: str) -> int:
    return 3 if es_lima(departamento) else 6 + DIAS_EXTRA.get(departamento, 0)


class EstrategiaEnvio(ABC):
    """Interfaz común: todas las estrategias responden a lo mismo."""

    def __init__(self, courier):
        self.courier = courier

    @property
    def nombre(self) -> str:
        return self.courier.nombre

    def atiende(self, departamento: str) -> bool:
        return True

    @abstractmethod
    def costo(self, departamento: str) -> Decimal: ...

    def cotizar(self, departamento: str) -> Decimal:
        if departamento is None:
            raise ValueError("El pedido no tiene departamento de destino")
        if not self.atiende(departamento):
            raise DestinoNoAtendido(f"{self.nombre} no reparte en {departamento}")
        return self.costo(departamento)

    def fecha_estimada(self, fecha_pedido: datetime, departamento: str) -> date:
        return (fecha_pedido + timedelta(days=dias_prometidos(departamento))).date()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.nombre}>"


class EnvioEstandar(EstrategiaEnvio):
    """Courier nacional: tarifa base + recargo fijo a provincia."""

    def costo(self, departamento):
        return self.courier.costo_base + (Decimal(0) if es_lima(departamento)
                                          else RECARGO_PROVINCIA)


class EnvioExpressLima(EstrategiaEnvio):
    """Courier express urbano: tarifa base, pero solo Lima Metropolitana."""

    def atiende(self, departamento):
        return es_lima(departamento)

    def costo(self, departamento):
        return self.courier.costo_base


def estrategia_para(courier) -> EstrategiaEnvio:
    """Fábrica: elige la estrategia que corresponde a cada courier."""
    return EnvioExpressLima(courier) if courier.nombre in SOLO_LIMA else EnvioEstandar(courier)


def comparar(estrategias, departamento: str) -> list[tuple[EstrategiaEnvio, Decimal, int]]:
    """Cotiza con todas las estrategias que atienden el destino, de menor a mayor costo."""
    opciones = [(e, e.costo(departamento), dias_prometidos(departamento))
                for e in estrategias if e.atiende(departamento)]
    return sorted(opciones, key=lambda o: o[1])
