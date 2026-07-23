from typing import List
from uuid import UUID
from datetime import date
from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from ..models import UsuarioPermitido, Pago
from ..schemas.auth import (
    CheckAuthOut,
    UsuarioPermitidoSchema,
    UsuarioPermitidoInSchema,
    UsuarioPermitidoUpdateSchema,
    NotificationsSummaryOut,
    NotificationItemSchema
)

router = Router()

ADMIN_EMAILS_PREDETERMINADOS = [
    "eduardo20032110@gmail.com",
    "tolteninmobiliaria@gmail.com",
    "tolteninmobiliaria13@gmail.com"
]

@router.get("/check", response=CheckAuthOut)
def check_auth(request, email: str):
    clean_email = email.strip().lower()
    
    # Asegurar que los correos admin principales queden registrados como admin activo
    if clean_email in ADMIN_EMAILS_PREDETERMINADOS:
        user, _ = UsuarioPermitido.objects.get_or_create(
            email__iexact=clean_email,
            defaults={
                'email': clean_email,
                'rol': 'admin',
                'activo': True,
                'nombre': 'Administrador'
            }
        )
        if user.rol != 'admin' or not user.activo:
            user.rol = 'admin'
            user.activo = True
            user.save()
        return {
            "is_authorized": True,
            "email": clean_email,
            "rol": user.rol,
            "nombre": user.nombre or "Administrador",
            "message": "Usuario autorizado como Administrador"
        }

    try:
        user = UsuarioPermitido.objects.get(email__iexact=clean_email)
        if user.activo:
            return {
                "is_authorized": True,
                "email": user.email,
                "rol": user.rol,
                "nombre": user.nombre or user.email,
                "message": "Usuario autorizado"
            }
        else:
            return {
                "is_authorized": False,
                "email": clean_email,
                "rol": None,
                "nombre": None,
                "message": "Tu solicitud de acceso ha sido registrada y está pendiente de aprobación por un administrador."
            }
    except UsuarioPermitido.DoesNotExist:
        # Si el correo intenta iniciar sesión por primera vez, se registra automáticamente como PENDIENTE (activo=False)
        UsuarioPermitido.objects.create(
            email=clean_email,
            nombre=clean_email.split('@')[0],
            rol='user',
            activo=False
        )
        return {
            "is_authorized": False,
            "email": clean_email,
            "rol": None,
            "nombre": None,
            "message": "Tu solicitud de acceso ha sido registrada y está pendiente de aprobación por un administrador."
        }

@router.get("/notifications", response=NotificationsSummaryOut)
def get_notifications(request):
    # 1. Usuarios pendientes de aprobación
    usuarios_pendientes = list(UsuarioPermitido.objects.filter(activo=False).order_by('-fecha_registro'))
    pending_items = [
        NotificationItemSchema(
            id=str(u.id),
            tipo="usuario_pendiente",
            titulo="Solicitud de acceso pendiente",
            descripcion=f"El correo {u.email} solicita autorización.",
            fecha=u.fecha_registro.strftime("%Y-%m-%d %H:%M"),
            link="/dashboard/usuarios"
        )
        for u in usuarios_pendientes
    ]

    # 2. Cuotas que vencen hoy o están vencidas y no pagadas
    today = date.today()
    cuotas_vencidas = list(
        Pago.objects.select_related('contrato__cliente', 'contrato__parcela')
        .filter(fecha_vencimiento__lte=today)
        .exclude(estado='pagado')
        .order_by('fecha_vencimiento')[:15]
    )
    
    due_items = [
        NotificationItemSchema(
            id=str(p.id),
            tipo="cuota_vencimiento",
            titulo=f"Cuota #{p.numero_cuota} {'vence hoy' if p.fecha_vencimiento == today else 'vencida'}",
            descripcion=f"Lote {p.contrato.parcela.numero_lote} ({p.contrato.cliente.nombre_completo}) - ${int(p.monto_cobrar):,}",
            fecha=p.fecha_vencimiento.strftime("%Y-%m-%d"),
            link="/vencimientos"
        )
        for p in cuotas_vencidas
    ]

    all_items = pending_items + due_items
    return NotificationsSummaryOut(
        total_count=len(all_items),
        pending_users_count=len(pending_items),
        due_today_count=len(due_items),
        items=all_items
    )

@router.get("/usuarios", response=List[UsuarioPermitidoSchema])
def list_usuarios(request):
    # Asegurar correos admin creados
    for admin_email in ADMIN_EMAILS_PREDETERMINADOS:
        UsuarioPermitido.objects.get_or_create(
            email__iexact=admin_email,
            defaults={
                'email': admin_email,
                'rol': 'admin',
                'activo': True,
                'nombre': 'Administrador'
            }
        )
    return UsuarioPermitido.objects.all().order_by('-fecha_registro')

@router.post("/usuarios", response=UsuarioPermitidoSchema)
def create_usuario(request, payload: UsuarioPermitidoInSchema):
    clean_email = payload.email.strip().lower()
    user, created = UsuarioPermitido.objects.get_or_create(
        email__iexact=clean_email,
        defaults={
            'email': clean_email,
            'nombre': payload.nombre,
            'rol': payload.rol,
            'activo': payload.activo
        }
    )
    if not created:
        user.nombre = payload.nombre or user.nombre
        user.rol = payload.rol
        user.activo = payload.activo
        user.save()
    return user

@router.patch("/usuarios/{user_id}", response=UsuarioPermitidoSchema)
def update_usuario(request, user_id: UUID, payload: UsuarioPermitidoUpdateSchema):
    user = get_object_or_404(UsuarioPermitido, id=user_id)
    
    # Proteger administradores predefinidos
    if user.email.lower() in ADMIN_EMAILS_PREDETERMINADOS:
        if payload.rol is not None and payload.rol != 'admin':
            raise HttpError(400, "Los administradores principales predeterminados no pueden ser cambiados de rol.")
        if payload.activo is not None and not payload.activo:
            raise HttpError(400, "Los administradores principales predeterminados no pueden ser desactivados.")
            
    if payload.nombre is not None:
        user.nombre = payload.nombre
    if payload.rol is not None:
        user.rol = payload.rol
    if payload.activo is not None:
        user.activo = payload.activo
    user.save()
    return user

@router.delete("/usuarios/{user_id}")
def delete_usuario(request, user_id: UUID):
    user = get_object_or_404(UsuarioPermitido, id=user_id)
    
    # Proteger administradores predefinidos
    if user.email.lower() in ADMIN_EMAILS_PREDETERMINADOS:
        raise HttpError(400, "Los administradores principales predeterminados no pueden ser eliminados.")
        
    user.delete()
    return {"success": True, "message": "Usuario eliminado correctamente"}
