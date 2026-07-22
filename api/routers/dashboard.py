from ninja import Router
from typing import List
from django.db.models import Sum
from datetime import date
from ..models import Contrato, Pago
from ..schemas.dashboard import DashboardStatsSchema, LotSchema

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

@router.get("/lots", response=List[LotSchema])
def listar_dashboard_lots(request):
    from collections import defaultdict
    from django.db.models import Sum, Q

    contratos = list(Contrato.objects.select_related('cliente', 'parcela').all())
    contrato_ids = [c.id for c in contratos]
    today = date.today()

    # Query all active payments of these contracts that are overdue
    pagos_vencidos_set = set(
        Pago.objects.filter(
            contrato_id__in=contrato_ids,
            estado='vencido'
        ).values_list('contrato_id', flat=True)
    ) | set(
        Pago.objects.filter(
            contrato_id__in=contrato_ids,
            estado='pendiente',
            fecha_vencimiento__lt=today
        ).values_list('contrato_id', flat=True)
    )

    # Get balance of pending/overdue payments grouped by contract in 1 query
    pagos_balance = (
        Pago.objects.filter(contrato_id__in=contrato_ids, estado__in=['pendiente', 'vencido'])
        .values('contrato_id')
        .annotate(total=Sum('monto_cobrar'))
    )
    balance_map = {item['contrato_id']: float(item['total'] or 0.0) for item in pagos_balance}

    # Get next due payment for each contract in 1 query (grouped)
    unpaid_pagos = Pago.objects.filter(contrato_id__in=contrato_ids, estado__in=['pendiente', 'vencido']).order_by('fecha_vencimiento')
    next_pagos_map = {}
    for p in unpaid_pagos:
        if p.contrato_id not in next_pagos_map:
            next_pagos_map[p.contrato_id] = p.fecha_vencimiento

    # Get last paid payment date for each contract in 1 query
    paid_pagos = Pago.objects.filter(contrato_id__in=contrato_ids, estado='pagado').order_by('-fecha_pago_real')
    last_payments_map = {}
    for p in paid_pagos:
        if p.contrato_id not in last_payments_map:
            last_payments_map[p.contrato_id] = p.fecha_pago_real

    # Fetch installment value (first payment of each contract) in one query
    first_payments = {
        p.contrato_id: p 
        for p in Pago.objects.filter(contrato_id__in=contrato_ids, numero_cuota=1)
    }

    resultado = []
    for c in contratos:
        status = "overdue" if c.id in pagos_vencidos_set else "current"
        saldo = balance_map.get(c.id, 0.0)
        
        next_due = next_pagos_map.get(c.id)
        next_due_date = next_due.strftime("%d/%m/%Y") if next_due else None

        last_pago_date = last_payments_map.get(c.id)
        last_payment_date = last_pago_date.strftime("%d/%m/%Y") if last_pago_date else None

        primer_pago = first_payments.get(c.id)
        installment_value = float(primer_pago.monto_cobrar) if primer_pago else 0.0

        resultado.append({
            "id": str(c.id),
            "lot": c.parcela.numero_lote,
            "owner": c.cliente.nombre_completo,
            "salePrice": float(c.parcela.precio_base),
            "downPayment": float(c.pie_inicial),
            "balance": float(saldo),
            "installmentCount": c.total_cuotas,
            "installmentValue": installment_value,
            "nextDueDate": next_due_date,
            "status": status,
            "lastPaymentDate": last_payment_date,
            "paymentMethod": "Transferencia"
        })
    return resultado
