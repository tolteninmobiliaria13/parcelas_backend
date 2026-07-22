from ninja import Schema
from typing import Optional
from datetime import date

class AsignarPropietarioInSchema(Schema):
    cliente_id: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_telefono: Optional[str] = None
    fecha_pago: date
    pie_inicial: float
    total_cuotas: int
    monto_cuota: float
    cuotas_pagadas: Optional[int] = 0

class ParcelaInSchema(Schema):
    numero_lote: str
    numero_rol: Optional[str] = None
    subdivision: str
    superficie_m2: Optional[float] = None
    precio_base: float
    estado: Optional[str] = 'disponible'

class ParcelaCompletaSchema(Schema):
    id: str
    owner: str
    surface: float
    escritura: str
    precioVenta: float
    abono: float
    saldo: float
    status: str
    subdivision: str
    estado: str

