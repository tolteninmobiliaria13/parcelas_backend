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
    tipo_pago: Optional[str] = 'credito'

class ParcelaInSchema(Schema):
    numero_lote: str
    numero_rol: Optional[str] = None
    subdivision: str
    precio_base: float
    estado: Optional[str] = 'disponible'

class ParcelaCompletaSchema(Schema):
    id: str
    owner: str
    escritura: str
    precioVenta: float
    abono: float
    saldo: float
    status: str
    subdivision: str
    estado: str

class PaginatedParcelaSchema(Schema):
    items: list[ParcelaCompletaSchema]
    total: int
    page: int
    pages: int

