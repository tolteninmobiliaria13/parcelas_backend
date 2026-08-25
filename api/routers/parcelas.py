from ninja import Router, Schema
from typing import List, Optional
from django.db.models import Sum
from ..models import Parcela, Contrato, Cliente, Pago
from ..schemas.parcelas import ParcelaCompletaSchema, ParcelaInSchema, AsignarPropietarioInSchema, PaginatedParcelaSchema, CambiarPropietarioInSchema, EditarContratoInSchema
from ..schemas.clientes import ClienteSchema, ClienteInSchema

router = Router()

def clave_orden_lote(p: Parcela):
    lote_str = p.numero_lote or ""
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

@router.get("/", response=PaginatedParcelaSchema)
def listar_parcelas(request, page: int = 1, limit: int = 20):
    import math

    todos_lotes = list(Parcela.objects.filter(en_papelera=False))
    todos_lotes.sort(key=clave_orden_lote)
    
    total = len(todos_lotes)
    pages = math.ceil(total / limit) if limit > 0 else 1
    offset = (page - 1) * limit
    
    parcelas = todos_lotes[offset:offset+limit]
    contratos = list(Contrato.objects.filter(estado='activo').select_related('cliente'))
    contratos_map = {c.parcela_id: c for c in contratos}

    resultado = []
    for p in parcelas:
        contrato = contratos_map.get(p.id)
        if contrato:
            owner = contrato.cliente.nombre_completo
            total_cuotas_esperado = contrato.total_cuotas * contrato.installment_value
            pagos_realizados = float(total_cuotas_esperado) - float(contrato.saldo_pendiente)
            abono = float(contrato.pie_inicial) + pagos_realizados
            saldo = float(contrato.saldo_pendiente)
            status = contrato.estado_calculado
        else:
            owner = "Sin Asignar"
            abono = 0.0
            saldo = 0.0
            status = "inactive"

        resultado.append({
            "id": p.numero_lote,
            "owner": owner,
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

class ParcelaPapeleraSchema(Schema):
    id: str
    numero_lote: str
    subdivision: str
    owner: str
    precio_base: float
    fecha_eliminacion: str | None = None

class MessageResponseSchema(Schema):
    success: bool
    message: str

def get_parcela_by_id_or_lote(lote_id: str):
    from django.db.models import Q
    from ninja.errors import HttpError
    parcela = Parcela.objects.filter(Q(id=lote_id) if len(lote_id) == 36 else Q(numero_lote=lote_id)).first()
    if not parcela:
        raise HttpError(404, f"Parcela {lote_id} no encontrada.")
    return parcela

@router.get("/papelera", response=List[ParcelaPapeleraSchema])
def listar_papelera(request):
    todos_papelera = list(Parcela.objects.filter(en_papelera=True))
    todos_papelera.sort(key=clave_orden_lote)
    
    contratos = list(Contrato.objects.all().select_related('cliente'))
    contratos_map = {c.parcela_id: c for c in contratos}

    resultado = []
    for p in todos_papelera:
        contrato = contratos_map.get(p.id)
        owner = contrato.cliente.nombre_completo if contrato else "Sin Asignar"
        fecha_elim_str = p.fecha_eliminacion.strftime("%d/%m/%Y %H:%M") if p.fecha_eliminacion else None
        
        resultado.append({
            "id": str(p.id),
            "numero_lote": p.numero_lote,
            "subdivision": p.subdivision,
            "owner": owner,
            "precio_base": float(p.precio_base),
            "fecha_eliminacion": fecha_elim_str
        })
    return resultado

@router.post("/", response={201: ParcelaCompletaSchema})
def crear_parcela(request, payload: ParcelaInSchema):
    parcela = Parcela.objects.create(
        numero_lote=payload.numero_lote,
        numero_rol=payload.numero_rol,
        subdivision=payload.subdivision,
        precio_base=payload.precio_base,
        estado=payload.estado or 'disponible'
    )
    return 201, {
        "id": parcela.numero_lote,
        "owner": "Sin Asignar",
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
    
    # Desactivar cualquier contrato activo previo para esta parcela
    Contrato.objects.filter(parcela=parcela, estado='activo').update(estado='finalizado')

    tipo_pago_val = payload.tipo_pago if payload.tipo_pago in ['contado', 'credito'] else ('contado' if payload.total_cuotas <= 1 else 'credito')
    contrato = Contrato.objects.create(
        cliente=cliente,
        parcela=parcela,
        fecha_pago=payload.fecha_pago,
        pie_inicial=payload.pie_inicial,
        total_cuotas=payload.total_cuotas,
        tipo_pago=tipo_pago_val,
        estado='activo'
    )
    
    cuotas_pagadas = payload.cuotas_pagadas or 0
    for i in range(1, payload.total_cuotas + 1):
        fecha_vencimiento = sumar_meses(payload.fecha_pago, i - 1)
        pago_estado = 'pagado' if i <= cuotas_pagadas else 'pendiente'
        fecha_pago_real = fecha_vencimiento if i <= cuotas_pagadas else None
        
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
        "escritura": parcela.numero_rol or "",
        "precioVenta": float(parcela.precio_base),
        "abono": abono_total,
        "saldo": saldo_total,
        "status": "current",
        "subdivision": parcela.subdivision,
        "estado": parcela.estado
    }

@router.put("/{lote_id}", response={200: ParcelaCompletaSchema})
def editar_parcela(request, lote_id: str, payload: ParcelaInSchema):
    from django.shortcuts import get_object_or_404
    parcela = get_object_or_404(Parcela, numero_lote=lote_id)
    
    parcela.numero_lote = payload.numero_lote
    if payload.numero_rol is not None:
        parcela.numero_rol = payload.numero_rol
    parcela.subdivision = payload.subdivision
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
        "escritura": parcela.numero_rol or "",
        "precioVenta": float(parcela.precio_base),
        "abono": abono,
        "saldo": saldo,
        "status": status,
        "subdivision": parcela.subdivision,
        "estado": parcela.estado
    }


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
    from django.db.models.deletion import ProtectedError, RestrictedError
    
    cliente = get_object_or_404(Cliente, id=cliente_id)
    try:
        cliente.delete()
    except (ProtectedError, RestrictedError):
        raise HttpError(400, "No se puede eliminar un cliente que tiene contratos asociados.")
    return {"success": True}

@router.put("/{lote_id}/propietario", response={200: ParcelaCompletaSchema})
def cambiar_propietario(request, lote_id: str, payload: CambiarPropietarioInSchema):
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
        if not payload.cliente_nombre:
            raise HttpError(400, "El nombre del cliente es obligatorio.")
        cliente = Cliente.objects.create(
            nombre_completo=payload.cliente_nombre,
            email=payload.cliente_email,
            telefono=payload.cliente_telefono
        )
        contrato.cliente = cliente

    contrato.save()

    pagos = contrato.pagos.all()
    abono = float(contrato.pie_inicial) + float(sum(p.monto_cobrar for p in pagos if p.estado == 'pagado'))
    saldo = float(sum(p.monto_cobrar for p in pagos if p.estado != 'pagado'))
    status = "overdue" if any(p.estado == 'vencido' for p in pagos) else "current"

    return 200, {
        "id": parcela.numero_lote,
        "owner": contrato.cliente.nombre_completo,
        "escritura": parcela.numero_rol or "",
        "precioVenta": float(parcela.precio_base),
        "abono": abono,
        "saldo": saldo,
        "status": status,
        "subdivision": parcela.subdivision,
        "estado": parcela.estado
    }

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
            
    tipo_pago_val = payload.tipo_pago if payload.tipo_pago in ['contado', 'credito'] else ('contado' if payload.total_cuotas <= 1 else 'credito')
    contrato.fecha_pago = payload.fecha_pago
    contrato.pie_inicial = payload.pie_inicial
    contrato.total_cuotas = payload.total_cuotas
    contrato.tipo_pago = tipo_pago_val
    contrato.save()
    
    contrato.pagos.all().delete()
    cuotas_pagadas = payload.cuotas_pagadas or 0
    for i in range(1, payload.total_cuotas + 1):
        fecha_vencimiento = sumar_meses(payload.fecha_pago, i - 1)
        pago_estado = 'pagado' if i <= cuotas_pagadas else 'pendiente'
        fecha_pago_real = fecha_vencimiento if i <= cuotas_pagadas else None
        
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
    tipo_pago: str

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
    fecha_pago_val = primer_pago.fecha_vencimiento if primer_pago else contrato.fecha_pago
    
    return 200, {
        "cliente_id": str(contrato.cliente.id),
        "cliente_nombre": contrato.cliente.nombre_completo,
        "fecha_pago": fecha_pago_val,
        "pie_inicial": float(contrato.pie_inicial),
        "total_cuotas": contrato.total_cuotas,
        "monto_cuota": monto_cuota,
        "cuotas_pagadas": cuotas_pagadas,
        "tipo_pago": contrato.tipo_pago or ("contado" if contrato.total_cuotas <= 1 and cuotas_pagadas == contrato.total_cuotas else "credito")
    }


@router.delete("/{lote_id}", response=MessageResponseSchema)
def mover_a_papelera(request, lote_id: str):
    from django.utils import timezone
    parcela = get_parcela_by_id_or_lote(lote_id)
    parcela.en_papelera = True
    parcela.fecha_eliminacion = timezone.now()
    parcela.save()
    return {"success": True, "message": f"La parcela {parcela.numero_lote} fue movida a la papelera."}

@router.put("/{lote_id}/restaurar", response=MessageResponseSchema)
def restaurar_de_papelera(request, lote_id: str):
    parcela = get_parcela_by_id_or_lote(lote_id)
    parcela.en_papelera = False
    parcela.fecha_eliminacion = None
    parcela.save()
    return {"success": True, "message": f"La parcela {parcela.numero_lote} ha sido restaurada."}

@router.delete("/{lote_id}/definitivo", response=MessageResponseSchema)
def eliminar_definitivamente(request, lote_id: str):
    from django.db import transaction
    from django.db.models.signals import post_delete
    from ..models import update_contrato_cache

    parcela = get_parcela_by_id_or_lote(lote_id)
    lote_num = parcela.numero_lote

    with transaction.atomic():
        # Desconectar temporalmente la señal para evitar recálculos redundantes en bucle por cada cuota
        post_delete.disconnect(update_contrato_cache, sender=Pago)
        try:
            contratos = Contrato.objects.filter(parcela=parcela)
            Pago.objects.filter(contrato__in=contratos).delete()
            contratos.delete()
            parcela.delete()
        finally:
            post_delete.connect(update_contrato_cache, sender=Pago)

    return {"success": True, "message": f"La parcela {lote_num} y sus datos asociados fueron eliminados definitivamente."}




