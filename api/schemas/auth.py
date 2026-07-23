from ninja import Schema
from uuid import UUID
from typing import Optional, List
from datetime import datetime

class CheckAuthOut(Schema):
    is_authorized: bool
    email: str
    rol: Optional[str] = None
    nombre: Optional[str] = None
    message: Optional[str] = None

class UsuarioPermitidoSchema(Schema):
    id: UUID
    email: str
    nombre: Optional[str] = None
    rol: str
    activo: bool
    fecha_registro: datetime

class UsuarioPermitidoInSchema(Schema):
    email: str
    nombre: Optional[str] = None
    rol: str = "user"
    activo: bool = True

class UsuarioPermitidoUpdateSchema(Schema):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None

class NotificationItemSchema(Schema):
    id: str
    tipo: str  # 'usuario_pendiente' | 'cuota_vencimiento'
    titulo: str
    descripcion: str
    fecha: str
    link: Optional[str] = None

class NotificationsSummaryOut(Schema):
    total_count: int
    pending_users_count: int
    due_today_count: int
    items: List[NotificationItemSchema]
