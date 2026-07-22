from ninja import Router, Schema
from typing import List
from django.db.models import Sum
from ..models import Parcela, Contrato, Cliente, Pago
from ..schemas.parcelas import ParcelaCompletaSchema, ParcelaInSchema, AsignarPropietarioInSchema, PaginatedParcelaSchema
from ..schemas.clientes import ClienteSchema, ClienteInSchema

router = Router()

@router.get("/", response=PaginatedParcelaSchema)
def listar_parcelas(request, page: int = 1, limit: int = 20):
    import math
    from collections import defaultdict
    from django.db.models import Sum

    queryset = Parcela.objects.all().order_by('numero_lote')
    total = queryset.count()
    pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    
    parcelas = list(queryset[offset:offset+limit])
    contratos = list(Contrato.objects.filter(estado='activo').select_related('cliente'))
    contratos_map = {c.parcela_id: c for c in contratos}

    # Fetch aggregated payments for active contracts
    pagos_data = Pago.objects.filter(contrato__estado='activo').values('contrato_id', 'estado').annotate(total=Sum('monto_cobrar'))
    
    # Identify contracts that have at least one overdue payment (either explicit 'vencido' or 'pendiente' ya vencido)
    from django.db.models import Q
    vencidos_set = set(
        Pago.objects.filter(
            Q(contrato__estado='activo') &
            (Q(estado='vencido') | Q(estado='pendiente', fecha_vencimiento__lt=date.today()))
        )
        .values_list('contrato_id', flat=True)
        .distinct()
    )

    pagos_map = defaultdict(lambda: {"pagado": 0.0, "pendiente_vencido": 0.0})
    for item in pagos_data:
        c_id = item['contrato_id']
        estado = item['estado']
        total = float(item['total'] or 0.0)
        if estado == 'pagado':
            pagos_map[c_id]["pagado"] = total
        elif estado in ['pendiente', 'vencido']:
            pagos_map[c_id]["pendiente_vencido"] += total

    resultado = []
    for p in parcelas:
        contrato = contratos_map.get(p.id)
        if contrato:
            owner = contrato.cliente.nombre_completo
            pagos_realizados = pagos_map[contrato.id]["pagado"]
            abono = float(contrato.pie_inicial) + pagos_realizados
            saldo = pagos_map[contrato.id]["pendiente_vencido"]
            status = "overdue" if contrato.id in vencidos_set else "current"
        else:
            owner = "Sin Asignar"
            abono = 0.0
            saldo = 0.0
            status = "inactive"

        resultado.append({
            "id": p.numero_lote,
            "owner": owner,
            "surface": float(p.superficie_m2) if p.superficie_m2 else 0.0,
            "escritura": p.numero_rol or "",
            "precioVenta": float(p.precio_base),
            "abono": float(abono),
            "saldo": float(saldo),
            "status": status,
            "subdivision": p.subdivision,
            "estado": p.estado
        })
    return {
        "items": resultado,
        "total": total,
        "page": page,
        "pages": pages
    }

@router.post("/", response={201: ParcelaCompletaSchema})
def crear_parcela(request, payload: ParcelaInSchema):
    parcela = Parcela.objects.create(
        numero_lote=payload.numero_lote,
        numero_rol=payload.numero_rol,
        subdivision=payload.subdivision,
        superficie_m2=payload.superficie_m2,
        precio_base=payload.precio_base,
        estado=payload.estado or 'disponible'
    )
    return 201, {
        "id": parcela.numero_lote,
        "owner": "Sin Asignar",
        "surface": float(parcela.superficie_m2) if parcela.superficie_m2 else 0.0,
        "escritura": parcela.numero_rol or "",
        "precioVenta": float(parcela.precio_base),
        "abono": 0.0,
        "saldo": 0.0,
        "status": "inactive",
        "subdivision": parcela.subdivision,
        "estado": parcela.estado
    }

from datetime import date
import calendar

def sumar_meses(fecha: date, meses: int) -> date:
    new_month = fecha.month - 1 + meses
    new_year = fecha.year + new_month // 12
    new_month = new_month % 12 + 1
    
    last_day = calendar.monthrange(new_year, new_month)[1]
    new_day = min(fecha.day, last_day)
    return date(new_year, new_month, new_day)

@router.get("/clientes", response=List[ClienteSchema])
def listar_todos_clientes(request):
    return Cliente.objects.all()

@router.post("/{lote_id}/asignar", response={200: ParcelaCompletaSchema})
def asignar_propietario(request, lote_id: str, payload: AsignarPropietarioInSchema):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    
    parcela = get_object_or_404(Parcela, numero_lote=lote_id)
    
    if payload.cliente_id:
        cliente = get_object_or_404(Cliente, id=payload.cliente_id)
    else:
        if not payload.cliente_nombre:
            raise HttpError(400, "El nombre del cliente es obligatorio para registrar un nuevo dueño.")
        cliente = Cliente.objects.create(
            nombre_completo=payload.cliente_nombre,
            email=payload.cliente_email,
            telefono=payload.cliente_telefono
        )
        
    parcela.estado = 'vendida'
    parcela.save()
    
    contrato = Contrato.objects.create(
        cliente=cliente,
        parcela=parcela,
        fecha_pago=payload.fecha_pago,
        pie_inicial=payload.pie_inicial,
        total_cuotas=payload.total_cuotas,
        estado='activo'
    )
    
    cuotas_pagadas = payload.cuotas_pagadas or 0
    for i in range(1, payload.total_cuotas + 1):
        fecha_vencimiento = sumar_meses(payload.fecha_pago, i - 1)
        pago_estado = 'pagado' if i <= cuotas_pagadas else 'pendiente'
        fecha_pago_real = payload.fecha_pago if i <= cuotas_pagadas else None
        
        Pago.objects.create(
            contrato=contrato,
            numero_cuota=i,
            monto_cobrar=payload.monto_cuota,
            fecha_vencimiento=fecha_vencimiento,
            fecha_pago_real=fecha_pago_real,
            estado=pago_estado
        )
        
    abono_total = float(payload.pie_inicial) + (cuotas_pagadas * float(payload.monto_cuota))
    saldo_total = (payload.total_cuotas - cuotas_pagadas) * float(payload.monto_cuota)
        
    return 200, {
        "id": parcela.numero_lote,
        "owner": cliente.nombre_completo,
        "surface": float(parcela.superficie_m2) if parcela.superficie_m2 else 0.0,
        "escritura": parcela.numero_rol or "",
        "precioVenta": float(parcela.precio_base),
        "abono": abono_total,
        "saldo": saldo_total,
        "status": "current",
        "subdivision": parcela.subdivision
    }

@router.put("/{lote_id}", response={200: ParcelaCompletaSchema})
def editar_parcela(request, lote_id: str, payload: ParcelaInSchema):
    from django.shortcuts import get_object_or_404
    parcela = get_object_or_404(Parcela, numero_lote=lote_id)
    
    parcela.numero_lote = payload.numero_lote
    if payload.numero_rol is not None:
        parcela.numero_rol = payload.numero_rol
    parcela.subdivision = payload.subdivision
    if payload.superficie_m2 is not None:
        parcela.superficie_m2 = payload.superficie_m2
    parcela.precio_base = payload.precio_base
    if payload.estado is not None:
        parcela.estado = payload.estado
        
    parcela.save()
    
    contrato = parcela.contrato_set.filter(estado='activo').first()
    owner_name = "Sin Asignar"
    abono = 0.0
    saldo = 0.0
    status = "inactive"
    if contrato:
        owner_name = contrato.cliente.nombre_completo
        pagos = contrato.pagos.all()
        abono = float(contrato.pie_inicial) + float(sum(p.monto_cobrar for p in pagos if p.estado == 'pagado'))
        saldo = float(sum(p.monto_cobrar for p in pagos if p.estado != 'pagado'))
        status = "overdue" if any(p.estado == 'vencido' for p in pagos) else "current"
        
    return 200, {
        "id": parcela.numero_lote,
        "owner": owner_name,
        "surface": float(parcela.superficie_m2) if parcela.superficie_m2 else 0.0,
        "escritura": parcela.numero_rol or "",
        "precioVenta": float(parcela.precio_base),
        "abono": abono,
        "saldo": saldo,
        "status": status,
        "subdivision": parcela.subdivision,
        "estado": parcela.estado
    }

@router.delete("/{lote_id}")
def eliminar_parcela(request, lote_id: str):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    from django.db.models.deletion import ProtectedError
    
    parcela = get_object_or_404(Parcela, numero_lote=lote_id)
    try:
        parcela.delete()
    except ProtectedError:
        raise HttpError(400, "No se puede eliminar una parcela que tiene un contrato activo o registros asociados.")
    return {"success": True}

@router.post("/clientes/crear", response={201: ClienteSchema})
def crear_cliente_api(request, payload: ClienteInSchema):
    cliente = Cliente.objects.create(
        nombre_completo=payload.nombre_completo,
        email=payload.email,
        telefono=payload.telefono
    )
    return 201, cliente

@router.put("/clientes/{cliente_id}", response={200: ClienteSchema})
def editar_cliente_api(request, cliente_id: str, payload: ClienteInSchema):
    from django.shortcuts import get_object_or_404
    cliente = get_object_or_404(Cliente, id=cliente_id)
    cliente.nombre_completo = payload.nombre_completo
    cliente.email = payload.email
    cliente.telefono = payload.telefono
    cliente.save()
    return 200, cliente

@router.delete("/clientes/{cliente_id}")
def eliminar_cliente_api(request, cliente_id: str):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    from django.db.models.deletion import ProtectedError
    
    cliente = get_object_or_404(Cliente, id=cliente_id)
    try:
        cliente.delete()
    except ProtectedError:
        raise HttpError(400, "No se puede eliminar un cliente que tiene contratos activos asociados.")
    return {"success": True}

@router.put("/{lote_id}/contrato", response={200: ParcelaCompletaSchema})
def editar_contrato(request, lote_id: str, payload: AsignarPropietarioInSchema):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    
    parcela = get_object_or_404(Parcela, numero_lote=lote_id)
    contrato = parcela.contrato_set.filter(estado='activo').first()
    if not contrato:
        raise HttpError(404, "No existe un contrato activo para esta parcela.")
        
    if payload.cliente_id:
        cliente = get_object_or_404(Cliente, id=payload.cliente_id)
        contrato.cliente = cliente
    else:
        if payload.cliente_nombre:
            cliente = Cliente.objects.create(
                nombre_completo=payload.cliente_nombre,
                email=payload.cliente_email,
                telefono=payload.cliente_telefono
            )
            contrato.cliente = cliente
            
    contrato.fecha_pago = payload.fecha_pago
    contrato.pie_inicial = payload.pie_inicial
    contrato.total_cuotas = payload.total_cuotas
    contrato.save()
    
    contrato.pagos.all().delete()
    cuotas_pagadas = payload.cuotas_pagadas or 0
    for i in range(1, payload.total_cuotas + 1):
        fecha_vencimiento = sumar_meses(payload.fecha_pago, i - 1)
        pago_estado = 'pagado' if i <= cuotas_pagadas else 'pendiente'
        fecha_pago_real = payload.fecha_pago if i <= cuotas_pagadas else None
        
        Pago.objects.create(
            contrato=contrato,
            numero_cuota=i,
            monto_cobrar=payload.monto_cuota,
            fecha_vencimiento=fecha_vencimiento,
            fecha_pago_real=fecha_pago_real,
            estado=pago_estado
        )
        
    abono_total = float(payload.pie_inicial) + (cuotas_pagadas * float(payload.monto_cuota))
    saldo_total = (payload.total_cuotas - cuotas_pagadas) * float(payload.monto_cuota)
    
    return 200, {
        "id": parcela.numero_lote,
        "owner": contrato.cliente.nombre_completo,
        "surface": float(parcela.superficie_m2) if parcela.superficie_m2 else 0.0,
        "escritura": parcela.numero_rol or "",
        "precioVenta": float(parcela.precio_base),
        "abono": abono_total,
        "saldo": saldo_total,
        "status": "current",
        "subdivision": parcela.subdivision,
        "estado": parcela.estado
    }

class ContratoDetalleSchema(Schema):
    cliente_id: str
    cliente_nombre: str
    fecha_pago: date
    pie_inicial: float
    total_cuotas: int
    monto_cuota: float
    cuotas_pagadas: int

@router.get("/{lote_id}/contrato", response={200: ContratoDetalleSchema})
def obtener_contrato_detalle(request, lote_id: str):
    from django.shortcuts import get_object_or_404
    from ninja.errors import HttpError
    
    parcela = get_object_or_404(Parcela, numero_lote=lote_id)
    contrato = parcela.contrato_set.filter(estado='activo').first()
    if not contrato:
        raise HttpError(404, "No existe un contrato activo para esta parcela.")
        
    pagos = contrato.pagos.all().order_by('numero_cuota')
    primer_pago = pagos.first()
    monto_cuota = float(primer_pago.monto_cobrar) if primer_pago else 0.0
    cuotas_pagadas = pagos.filter(estado='pagado').count()
    
    return 200, {
        "cliente_id": str(contrato.cliente.id),
        "cliente_nombre": contrato.cliente.nombre_completo,
        "fecha_pago": contrato.fecha_pago,
        "pie_inicial": float(contrato.pie_inicial),
        "total_cuotas": contrato.total_cuotas,
        "monto_cuota": monto_cuota,
        "cuotas_pagadas": cuotas_pagadas
    }



