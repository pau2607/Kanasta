"""Patrón Decorator — descuentos acumulables.

Se parte de un `PrecioBase` (Σ cantidad × precio) y se le van "envolviendo"
descuentos. Cada decorador aplica su rebaja sobre el monto que le entrega
el anterior, así que se acumulan en cadena:

    precio = DescuentoMontoFijo(
                 DescuentoPorVolumen(
                     DescuentoCupon(PrecioBase(items), cupon), unidades),
                 10)

El orden importa: un 10 % y luego S/ 10 no es lo mismo que S/ 10 y luego 10 %.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

CERO = Decimal(0)


class Precio(ABC):
    """Componente: algo que sabe cuánto cuesta y cómo se llegó a ese monto."""

    @abstractmethod
    def monto(self) -> Decimal: ...

    @abstractmethod
    def lineas(self) -> list[tuple[str, Decimal]]:
        """Desglose: [(etiqueta, monto), ...] para mostrar en la boleta."""


class PrecioBase(Precio):
    """Componente concreto: suma de los ítems, sin descuentos."""

    def __init__(self, items):
        self._items = items

    def monto(self) -> Decimal:
        return sum((i.importe for i in self._items), CERO)

    def lineas(self):
        return [("Subtotal", self.monto())]


class Descuento(Precio, ABC):
    """Decorador base: envuelve otro `Precio` y le resta algo."""

    def __init__(self, envuelto: Precio):
        self._envuelto = envuelto

    @abstractmethod
    def rebaja(self, base: Decimal) -> Decimal:
        """Cuánto se descuenta sobre `base` (el monto que llega del anterior)."""

    @abstractmethod
    def etiqueta(self) -> str: ...

    def monto(self) -> Decimal:
        base = self._envuelto.monto()
        return max(CERO, base - self.rebaja(base))   # nunca negativo

    def lineas(self):
        base = self._envuelto.monto()
        aplicado = min(self.rebaja(base), base)
        return self._envuelto.lineas() + [(self.etiqueta(), -aplicado)]


class DescuentoPorcentaje(Descuento):
    def __init__(self, envuelto: Precio, pct, motivo: str = "Descuento"):
        super().__init__(envuelto)
        if not 0 < Decimal(pct) <= 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")
        self.pct = Decimal(pct)
        self.motivo = motivo

    def rebaja(self, base):
        return base * self.pct / 100

    def etiqueta(self):
        return f"{self.motivo} (-{self.pct:g}%)"


class DescuentoCupon(DescuentoPorcentaje):
    """El descuento que ya existe en la BD (cupones.descuento_pct)."""

    def __init__(self, envuelto: Precio, cupon):
        super().__init__(envuelto, cupon.descuento_pct, f"Cupón {cupon.codigo}")
        self.cupon = cupon


class DescuentoPorVolumen(DescuentoPorcentaje):
    """X % si se compran al menos N unidades ("descuento por mayor")."""

    def __init__(self, envuelto: Precio, unidades: int, min_unidades: int = 6, pct=5):
        super().__init__(envuelto, pct, f"Por volumen ({min_unidades}+ u.)")
        self.aplica = unidades >= min_unidades

    def rebaja(self, base):
        return super().rebaja(base) if self.aplica else CERO


class DescuentoMedioPago(DescuentoPorcentaje):
    """Promoción por pagar con cierto medio (ej. 3 % con Yape)."""

    def __init__(self, envuelto: Precio, metodo: str, pct):
        super().__init__(envuelto, pct, f"Pago con {metodo}")
        self.metodo = metodo


class DescuentoMontoFijo(Descuento):
    """Rebaja fija en soles (ej. S/ 10 de bienvenida)."""

    def __init__(self, envuelto: Precio, soles, motivo: str = "Descuento fijo"):
        super().__init__(envuelto)
        self.soles = Decimal(str(soles))
        self.motivo = motivo

    def rebaja(self, base):
        return self.soles

    def etiqueta(self):
        return f"{self.motivo} (-S/ {self.soles:,.2f})"
