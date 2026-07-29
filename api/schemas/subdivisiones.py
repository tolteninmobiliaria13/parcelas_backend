from ninja import Schema
from typing import Optional

class SubdivisionInSchema(Schema):
    nombre: str

class SubdivisionSchema(Schema):
    id: str
    numero: Optional[int] = None
    nombre: str
