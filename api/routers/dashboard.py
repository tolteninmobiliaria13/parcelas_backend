from ninja import Router
from typing import List
from django.db.models import Sum
from datetime import date
from ..models import Contrato, Pago
from ..schemas.dashboard import DashboardStatsSchema, LotSchema, PaginatedLotSchema

router = Router()

@router.get("/stats", response=DashboardStatsSchema)
def obtener_dashboard_stats(request):
    today = date.today()
    # total_por_pagar: cuotas del mes actual que aún no han sido pagadas
    unpaid_this_month = Pago.objects.filter(
        estado__in=['pendiente', 'vencido'],
        fecha_vencimiento__year=today.year,
        fecha_vencimiento__month=today.month,
    )
    total_por_pagar = unpaid_this_month.aggregate(total=Sum('monto_cobrar'))['total'] or 0.0
    paid_this_month = Pago.objects.filter(
        estado='pagado', 
        fecha_pago_real__year=today.year, 
        fecha_pago_real__month=today.month
    )
    total_pagado_mes = paid_this_month.aggregate(total=Sum('monto_cobrar'))['total'] or 0.0

    # lotes_con_deuda: cantidad de parcelas con pagos vencidos (estado 'vencido' o 'pendiente' ya vencido)
    from django.db.models import Q
    lotes_con_deuda = (
        Contrato.objects.filter(
            Q(pagos__estado='vencido') |
            Q(pagos__estado='pendiente', pagos__fecha_vencimiento__lt=today)
        )
        .values('parcela')
        .distinct()
        .count()
    )

    # proximos_vencimientos: cantidad de cuotas pendientes que vencen en el mes actual y no están vencidas
    proximos_vencimientos = Pago.objects.filter(
        estado='pendiente', 
        fecha_vencimiento__year=today.year, 
        fecha_vencimiento__month=today.month,
        fecha_vencimiento__gte=today
    ).count()

    return {
        "total_por_pagar": float(total_por_pagar),
        "total_pagado_mes": float(total_pagado_mes),
        "lotes_con_deuda": lotes_con_deuda,
        "proximos_vencimientos": proximos_vencimientos
    }

@router.get("/lots", response=PaginatedLotSchema)
def listar_dashboard_lots(request, page: int = 1, limit: int = 20):
    import math

    queryset = Contrato.objects.select_related('cliente', 'parcela').all().order_by('id')
    total = queryset.count()
    pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    
    contratos = list(queryset[offset:offset+limit])
    
    resultado = []
    for c in contratos:
        next_due_date = c.proximo_vencimiento.strftime("%d/%m/%Y") if c.proximo_vencimiento else None
        last_payment_date = c.ultimo_pago.strftime("%d/%m/%Y") if c.ultimo_pago else None

        resultado.append({
            "id": str(c.id),
            "lot": c.parcela.numero_lote,
            "owner": c.cliente.nombre_completo,
            "salePrice": float(c.parcela.precio_base),
            "downPayment": float(c.pie_inicial),
            "balance": float(c.saldo_pendiente),
            "installmentCount": c.total_cuotas,
            "installmentValue": float(c.installment_value),
            "nextDueDate": next_due_date,
            "status": c.estado_calculado,
            "lastPaymentDate": last_payment_date,
            "paymentMethod": "Transferencia"
        })
    return {
        "items": resultado,
        "total": total,
        "page": page,
        "pages": pages
    }
