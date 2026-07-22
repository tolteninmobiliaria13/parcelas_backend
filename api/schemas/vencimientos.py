from ninja import Schema
from typing import List, Optional

class MonthlyPaymentSchema(Schema):
    id: str
    month: str
    year: int
    status: str
    amount: float
    dueDate: Optional[str] = None
    paidDate: Optional[str] = None
    receiptNumber: Optional[str] = None
    daysOverdue: Optional[int] = None

class LotPaymentMatrixSchema(Schema):
    id: str
    lotNumber: str
    clientName: str
    project: str
    paidMonths: int
    overdueMonths: int
    totalMonths: int
    installmentAmount: float
    payments: List[MonthlyPaymentSchema]
