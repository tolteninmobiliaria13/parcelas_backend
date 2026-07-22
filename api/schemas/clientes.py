from ninja import Schema
from uuid import UUID
from typing import Optional

class ClienteSchema(Schema):
    id: UUID
    nombre_completo: str
    email: Optional[str] = None
    telefono: Optional[str] = None

class ClienteInSchema(Schema):
    nombre_completo: str
    email: Optional[str] = None
    telefono: Optional[str] = None

