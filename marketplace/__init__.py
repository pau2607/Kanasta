"""P4 — Marketplace multivendedor: clases y patrones de diseño."""
from .builder import ErrorPedido, PedidoBuilder
from .descuentos import (DescuentoCupon, DescuentoMedioPago, DescuentoMontoFijo,
                         DescuentoPorcentaje, DescuentoPorVolumen, PrecioBase)
from .envios import (DestinoNoAtendido, EnvioEstandar, EnvioExpressLima, comparar,
                     estrategia_para)
from .estados import TransicionInvalida
from .modelos import Courier, Cupon, ItemPedido, Pedido, Variante, dinero
