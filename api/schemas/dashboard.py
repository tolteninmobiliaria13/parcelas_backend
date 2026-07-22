from ninja import Schema
from typing import Optional

class DashboardStatsSchema(Schema):
    total_por_pagar: float
    total_pagado_mes: float
    lotes_con_deuda: int
    proximos_vencimientos: int

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
    lastPaymentDate: Optional[str] = None
    paymentMethod: Optional[str] = None

class PaginatedLotSchema(Schema):
    items: list[LotSchema]
    total: int
    page: int
    pages: int
