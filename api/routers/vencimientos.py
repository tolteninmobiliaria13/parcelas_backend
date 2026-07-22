from ninja import Router, Schema
from typing import List, Optional
from datetime import date
from ..models import Contrato, Pago
from ..schemas.vencimientos import LotPaymentMatrixSchema, MonthlyPaymentSchema

router = Router()

SPANISH_MONTHS = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

@router.get("/", response=List[LotPaymentMatrixSchema])
def obtener_vencimientos(request, year: int = 2025):
    from collections import defaultdict
    from django.db.models import Count

    contratos = list(Contrato.objects.select_related('cliente', 'parcela').all())
    contrato_ids = [c.id for c in contratos]

    # Fetch all payments for these contracts for the given year in one query
    pagos_anio = Pago.objects.filter(contrato_id__in=contrato_ids, fecha_vencimiento__year=year).order_by('fecha_vencimiento')
    pagos_anio_map = defaultdict(list)
    for p in pagos_anio:
        pagos_anio_map[p.contrato_id].append(p)

    # Fetch all payments of the active contracts in one query to compute paid/overdue counts dynamically
    pagos_all = Pago.objects.filter(contrato_id__in=contrato_ids).values('contrato_id', 'estado', 'fecha_vencimiento')
    counts_map = defaultdict(lambda: {"pagado": 0, "vencido": 0})
    today = date.today()
    for p_stat in pagos_all:
        c_id = p_stat['contrato_id']
        estado = p_stat['estado']
        due_date = p_stat['fecha_vencimiento']
        if estado == 'pagado':
            counts_map[c_id]["pagado"] += 1
        elif estado == 'vencido' or (estado == 'pendiente' and due_date < today):
            counts_map[c_id]["vencido"] += 1

    # Fetch installment amount (first payment of each contract) in one query
    first_payments = {
        p.contrato_id: p 
        for p in Pago.objects.filter(contrato_id__in=contrato_ids, numero_cuota=1)
    }

    resultado = []
    for c in contratos:
        pagos_anio_list = pagos_anio_map[c.id]
        paid_count = counts_map[c.id]["pagado"]
        overdue_count = counts_map[c.id]["vencido"]
        
        primer_pago = first_payments.get(c.id)
        installment_amount = float(primer_pago.monto_cobrar) if primer_pago else 0.0

        payments_list = []
        for m in range(1, 13):
            p = next((x for x in pagos_anio_list if x.fecha_vencimiento.month == m), None)
            month_name = SPANISH_MONTHS.get(m, 'Enero')
            
            if p:
                days_overdue = None
                p_status = p.estado
                if p_status == 'pendiente' and p.fecha_vencimiento < today:
                    p_status = 'vencido'
                
                if p_status == 'vencido':
                    delta = today - p.fecha_vencimiento
                    days_overdue = max(delta.days, 0)
                
                payments_list.append({
                    "id": str(p.id),
                    "month": month_name,
                    "year": p.fecha_vencimiento.year,
                    "status": p_status,
                    "amount": float(p.monto_cobrar),
                    "dueDate": p.fecha_vencimiento.strftime("%d/%m/%Y"),
                    "paidDate": p.fecha_pago_real.strftime("%d/%m/%Y") if p.fecha_pago_real else None,
                    "receiptNumber": f"REC-{p.fecha_vencimiento.year}-{p.id.hex[:4].upper()}" if p_status == 'pagado' else None,
                    "daysOverdue": days_overdue
                })
            else:
                payments_list.append({
                    "id": "",
                    "month": month_name,
                    "year": year,
                    "status": "none",
                    "amount": 0.0,
                    "dueDate": None,
                    "paidDate": None,
                    "receiptNumber": None,
                    "daysOverdue": None
                })

        resultado.append({
            "id": str(c.id),
            "lotNumber": c.parcela.numero_lote,
            "clientName": c.cliente.nombre_completo,
            "project": c.parcela.subdivision,
            "paidMonths": paid_count,
            "overdueMonths": overdue_count,
            "totalMonths": c.total_cuotas,
            "installmentAmount": installment_amount,
            "payments": payments_list
        })
    return resultado

class PagoUpdateSchema(Schema):
    monto_cobrar: Optional[float] = None
    fecha_vencimiento: Optional[date] = None
    fecha_pago_real: Optional[date] = None
    estado: Optional[str] = None

@router.put("/pagos/{pago_id}", response={200: MonthlyPaymentSchema})
def actualizar_pago(request, pago_id: str, payload: PagoUpdateSchema):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    
    pago = get_object_or_404(Pago, id=pago_id)
    
    if payload.monto_cobrar is not None:
        pago.monto_cobrar = payload.monto_cobrar
        
    if payload.fecha_vencimiento is not None:
        pago.fecha_vencimiento = payload.fecha_vencimiento
        
    if 'fecha_pago_real' in payload.dict(exclude_unset=True):
        pago.fecha_pago_real = payload.fecha_pago_real
        
    if payload.estado is not None:
        if payload.estado not in ['pendiente', 'pagado', 'vencido']:
            raise HttpError(400, "Estado inválido")
        pago.estado = payload.estado
        if payload.estado == 'pagado' and not pago.fecha_pago_real:
            pago.fecha_pago_real = date.today()
        elif payload.estado != 'pagado':
            pago.fecha_pago_real = None
            
    pago.save()
    
    month_name = SPANISH_MONTHS.get(pago.fecha_vencimiento.month, 'Enero')
    days_overdue = None
    if pago.estado == 'vencido':
        delta = date.today() - pago.fecha_vencimiento
        days_overdue = max(delta.days, 0)
        
    return 200, {
        "id": str(pago.id),
        "month": month_name,
        "year": pago.fecha_vencimiento.year,
        "status": pago.estado,
        "amount": float(pago.monto_cobrar),
        "dueDate": pago.fecha_vencimiento.strftime("%d/%m/%Y"),
        "paidDate": pago.fecha_pago_real.strftime("%d/%m/%Y") if pago.fecha_pago_real else None,
        "receiptNumber": f"REC-{pago.fecha_vencimiento.year}-{pago.id.hex[:4].upper()}" if pago.estado == 'pagado' else None,
        "daysOverdue": days_overdue
    }

