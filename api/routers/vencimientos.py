from ninja import Router, Schema
from typing import List, Optional
from datetime import date
from django.http import HttpResponse
from django.template import Template, Context
from pathlib import Path
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


def format_clp(amount):
    val = int(round(amount or 0))
    formatted = f"{val:,}".replace(",", ".")
    return f"$ {formatted}"


def obtener_datos_reporte_mes_actual():
    from collections import defaultdict
    today = date.today()
    month = today.month
    year = today.year
    fecha_emision = today.strftime("%d-%m-%Y")
    mes_str = SPANISH_MONTHS.get(month, 'Enero')
    periodo_str = f"{mes_str} {year}"
    
    contratos = Contrato.objects.select_related('cliente', 'parcela').all()
    
    # Fetch all payments as dicts to avoid instantiating thousands of Django models (10x faster)
    pagos_all = Pago.objects.values(
        'id', 'contrato_id', 'monto_cobrar', 'fecha_vencimiento', 'fecha_pago_real', 'estado'
    ).order_by('fecha_vencimiento')
    
    pagos_por_contrato = defaultdict(list)
    for p in pagos_all:
        pagos_por_contrato[p['contrato_id']].append(p)
    
    # Acumuladores para el Resumen Ejecutivo
    facturacion_periodo = 0.0
    cobranza_corriente = 0.0
    recuperacion_mora = 0.0
    
    # Contadores para el Estado de Cobranza
    estado_lotes = {
        "Al día": {"count": 0, "monto": 0.0},
        "Vencidos": {"count": 0, "monto": 0.0},
        "En mora": {"count": 0, "monto": 0.0},
    }
    
    detalles = []
    
    for c in contratos:
        pagos = pagos_por_contrato[c.id]
        
        # === 1. Lógica para Resumen Ejecutivo ===
        
        # Pagos que VENCEN este mes (Facturación del período)
        pago_mes = next((p for p in pagos if p['fecha_vencimiento'].month == month and p['fecha_vencimiento'].year == year), None)
        if pago_mes:
            facturacion_periodo += float(pago_mes['monto_cobrar'])
            if pago_mes['estado'] == 'pagado' and pago_mes['fecha_pago_real'] and pago_mes['fecha_pago_real'].month == month and pago_mes['fecha_pago_real'].year == year:
                cobranza_corriente += float(pago_mes['monto_cobrar'])
                
        # Pagos que VENCEN OTROS MESES pero se PAGARON este mes (Recuperación de mora o pagos adelantados)
        pagos_otros_meses_pagados_este_mes = [
            p for p in pagos 
            if (p['fecha_vencimiento'].month != month or p['fecha_vencimiento'].year != year)
            and p['estado'] == 'pagado'
            and p['fecha_pago_real']
            and p['fecha_pago_real'].month == month 
            and p['fecha_pago_real'].year == year
        ]
        
        for p_extra in pagos_otros_meses_pagados_este_mes:
            recuperacion_mora += float(p_extra['monto_cobrar'])
            
        # === 2. Lógica para Detalle de Cartera y Estado de Cobranza ===
        
        # Determinar el estado global del lote basado en cuotas vencidas/pendientes
        # Cuotas impagas pasadas o actuales
        cuotas_impagas = [
            p for p in pagos 
            if (p['estado'] == 'vencido') or (p['estado'] == 'pendiente' and p['fecha_vencimiento'] < today)
        ]
        
        deuda_total_lote = sum(float(p['monto_cobrar']) for p in cuotas_impagas)
        
        if len(cuotas_impagas) == 0:
            estado_lote_str = "Al día"
        elif len(cuotas_impagas) == 1:
            estado_lote_str = "Vencidos"  # o "Vencido"
        else:
            estado_lote_str = "En mora"
            
        estado_lotes[estado_lote_str]["count"] += 1
        estado_lotes[estado_lote_str]["monto"] += deuda_total_lote if deuda_total_lote > 0 else (float(pago_mes['monto_cobrar']) if pago_mes else 0)
        
        # Próximo Vencimiento (la primera cuota pendiente)
        prox_vencimiento = next((p['fecha_vencimiento'] for p in pagos if p['estado'] == 'pendiente' or p['estado'] == 'vencido'), None)
        prox_vencimiento_str = prox_vencimiento.strftime("%d-%m-%Y") if prox_vencimiento else "-"
        
        # Último Pago (el último pagado por fecha de pago real)
        pagos_realizados = [p for p in pagos if p['estado'] == 'pagado' and p['fecha_pago_real']]
        if pagos_realizados:
            ultimo_pago = max(pagos_realizados, key=lambda p: p['fecha_pago_real'])
            ultimo_pago_str = ultimo_pago['fecha_pago_real'].strftime("%d-%m-%Y")
        else:
            ultimo_pago_str = "-"
            
        detalles.append({
            "numero_lote": c.parcela.numero_lote,
            "propietario": c.cliente.nombre_completo,
            "estado": estado_lote_str,
            "saldo_fmt": format_clp(deuda_total_lote),
            "proximo_vencimiento": prox_vencimiento_str,
            "ultimo_pago": ultimo_pago_str
        })

    # === Ordenar Detalles ===
    def extraer_numero(item):
        import re
        match = re.search(r'\d+', item['numero_lote'])
        return int(match.group()) if match else 999999

    detalles.sort(key=extraer_numero)
    
    # === Cálculos Finales Resumen Ejecutivo ===
    cobranza_efectiva = cobranza_corriente + recuperacion_mora
    cuentas_por_cobrar = facturacion_periodo - cobranza_corriente
    
    # === Formateo de Estado de Cobranza ===
    estado_cobranza = [
        {
            "estado": "Al día",
            "lotes": estado_lotes["Al día"]["count"],
            "monto_fmt": format_clp(estado_lotes["Al día"]["monto"])
        },
        {
            "estado": "Vencidos",
            "lotes": estado_lotes["Vencidos"]["count"],
            "monto_fmt": format_clp(estado_lotes["Vencidos"]["monto"])
        },
        {
            "estado": "En mora",
            "lotes": estado_lotes["En mora"]["count"],
            "monto_fmt": format_clp(estado_lotes["En mora"]["monto"])
        }
    ]
    
    total_lotes = sum(item["lotes"] for item in estado_cobranza)
    total_monto_estado = sum(estado_lotes[k]["monto"] for k in estado_lotes)
    
    resumen_ejecutivo = {
        "facturacion_periodo_fmt": format_clp(facturacion_periodo),
        "cobranza_efectiva_fmt": format_clp(cobranza_efectiva),
        "recuperacion_mora_fmt": format_clp(recuperacion_mora),
        "cobranza_corriente_fmt": format_clp(cobranza_corriente),
        "cuentas_por_cobrar_fmt": format_clp(cuentas_por_cobrar),
    }

    proyectos = list(set(c.parcela.subdivision for c in contratos if c.parcela and c.parcela.subdivision))
    if len(proyectos) == 1:
        proyecto_nombre = proyectos[0]
    elif len(proyectos) > 1:
        proyecto_nombre = "Varios Proyectos"
    else:
        proyecto_nombre = "Sistema de Parcelas"
        
    return {
        "proyecto_nombre": proyecto_nombre,
        "periodo": periodo_str,
        "fecha_emision": fecha_emision,
        "resumen_ejecutivo": resumen_ejecutivo,
        "estado_cobranza": estado_cobranza,
        "total_estado_cobranza": {
            "lotes": total_lotes,
            "monto_fmt": format_clp(total_monto_estado)
        },
        "detalles": detalles,
    }


@router.get("/reporte-data")
def obtener_reporte_data(request):
    return obtener_datos_reporte_mes_actual()


@router.get("/reporte")
def generar_reporte_html(request):
    data = obtener_datos_reporte_mes_actual()
    template_path = Path(__file__).resolve().parent.parent.parent / "Resumen_Pagos_Parcelas.htm"
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()
        
    template = Template(template_content)
    context = Context(data)
    html_rendered = template.render(context)
    return HttpResponse(html_rendered, content_type="text/html; charset=utf-8")



