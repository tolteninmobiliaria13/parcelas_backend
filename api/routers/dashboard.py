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
        contrato__parcela__en_papelera=False,
        estado__in=['pendiente', 'vencido'],
        fecha_vencimiento__year=today.year,
        fecha_vencimiento__month=today.month,
    )
    total_por_pagar = unpaid_this_month.aggregate(total=Sum('monto_cobrar'))['total'] or 0.0
    paid_this_month = Pago.objects.filter(
        contrato__parcela__en_papelera=False,
        estado='pagado', 
        fecha_vencimiento__year=today.year, 
        fecha_vencimiento__month=today.month
    )
    total_pagado_mes = paid_this_month.aggregate(total=Sum('monto_cobrar'))['total'] or 0.0

    # lotes_con_deuda: cantidad de parcelas con pagos vencidos (estado 'vencido' o 'pendiente' ya vencido)
    from django.db.models import Q
    lotes_con_deuda = (
        Contrato.objects.filter(
            parcela__en_papelera=False
        ).filter(
            Q(pagos__estado='vencido') |
            Q(pagos__estado='pendiente', pagos__fecha_vencimiento__lt=today)
        )
        .values('parcela')
        .distinct()
        .count()
    )

    # proximos_vencimientos: cantidad de cuotas pendientes que vencen en el mes actual y no están vencidas
    proximos_vencimientos = Pago.objects.filter(
        contrato__parcela__en_papelera=False,
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

def clave_orden_lote_contrato(c: Contrato):
    lote_str = c.parcela.numero_lote or ""
    parts = lote_str.strip().split("-")
    prefix = parts[0].strip().upper() if len(parts) > 0 else ""
    
    num = 0
    if len(parts) > 1 and parts[1].strip().isdigit():
        num = int(parts[1].strip())
        
    has_sub = len(parts) > 2
    sub_is_num = False
    sub_num = 0
    sub_str = ""
    
    if has_sub:
        sub_val = parts[2].strip()
        if sub_val.isdigit():
            sub_is_num = True
            sub_num = int(sub_val)
        else:
            sub_str = sub_val.upper()
            
    return (prefix, num, 1 if has_sub else 0, 0 if sub_is_num else 1, sub_num, sub_str)

@router.get("/lots", response=PaginatedLotSchema)
def listar_dashboard_lots(request, page: int = 1, limit: int = 20):
    import math

    todos_contratos = list(Contrato.objects.filter(parcela__en_papelera=False).select_related('cliente', 'parcela').all())
    todos_contratos.sort(key=clave_orden_lote_contrato)
    
    total = len(todos_contratos)
    pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    
    contratos = todos_contratos[offset:offset+limit]
    
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
