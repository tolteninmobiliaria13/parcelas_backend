from ninja import Schema
from typing import Optional

class DashboardStatsSchema(Schema):
    total_por_pagar: float
    total_pagado_mes: float
    pagos_atrasados: float
    total_recaudado: float

class LotSchema(Schema):
    id: str
    lot: str
    owner: str
    salePrice: float
    downPayment: float
    balance: float
    installmentCount: int
    installmentValue: float
    nextDueDate: Optional[str] = None
    status: str
    overdueCount: int = 0
    overdueBalance: float = 0.0
    lastPaymentDate: Optional[str] = None
    paymentMethod: Optional[str] = None

class PaginatedLotSchema(Schema):
    items: list[LotSchema]
    total: int
    page: int
    pages: int
