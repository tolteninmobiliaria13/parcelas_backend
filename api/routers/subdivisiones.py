from typing import List
from ninja import Router
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from ..models import Subdivision, Parcela
from ..schemas.subdivisiones import SubdivisionSchema, SubdivisionInSchema

router = Router()

@router.get("/", response=List[SubdivisionSchema])
def listar_subdivisiones(request):
    subdivisiones = list(Subdivision.objects.all())
    subdivisiones.sort(key=lambda s: (s.numero if s.numero is not None else 999999, s.nombre.lower()))
    
    resultado = []
    for s in subdivisiones:
        resultado.append({
            "id": str(s.id),
            "numero": s.numero,
            "nombre": s.nombre,
        })
    return resultado

@router.post("/", response={201: SubdivisionSchema})
def crear_subdivision(request, payload: SubdivisionInSchema):
    nombre_clean = payload.nombre.strip()
    if not nombre_clean:
        raise HttpError(400, "El nombre de la subdivisión no puede estar vacío.")

    # Verificar si ya existe una subdivisión con ese nombre
    if Subdivision.objects.filter(nombre__iexact=nombre_clean).exists():
        raise HttpError(400, f"Ya existe una subdivisión con el nombre '{nombre_clean}'.")

    # Autoincremento secuencial inteligente: buscar el número máximo
    max_num = Subdivision.objects.exclude(numero=None).order_by('-numero').first()
    siguiente_numero = (max_num.numero + 1) if (max_num and max_num.numero) else 1

    sub = Subdivision.objects.create(
        numero=siguiente_numero,
        nombre=nombre_clean
    )

    return 201, {
        "id": str(sub.id),
        "numero": sub.numero,
        "nombre": sub.nombre,
    }

@router.put("/{subdivision_id}", response={200: SubdivisionSchema})
def editar_subdivision(request, subdivision_id: str, payload: SubdivisionInSchema):
    sub = get_object_or_404(Subdivision, id=subdivision_id)
    nuevo_nombre = payload.nombre.strip()
    if not nuevo_nombre:
        raise HttpError(400, "El nombre de la subdivisión no puede estar vacío.")

    if Subdivision.objects.filter(nombre__iexact=nuevo_nombre).exclude(id=sub.id).exists():
        raise HttpError(400, f"Ya existe otra subdivisión registrada con el nombre '{nuevo_nombre}'.")

    nombre_antiguo = sub.nombre
    sub.nombre = nuevo_nombre
    sub.save()

    # Actualizar la referencia de nombre en las parcelas asociadas
    Parcela.objects.filter(subdivision=nombre_antiguo).update(subdivision=nuevo_nombre)
    Parcela.objects.filter(subdivision_ref=sub).update(subdivision=nuevo_nombre)

    return 200, {
        "id": str(sub.id),
        "numero": sub.numero,
        "nombre": sub.nombre,
    }

@router.delete("/{subdivision_id}")
def eliminar_subdivision(request, subdivision_id: str):
    sub = get_object_or_404(Subdivision, id=subdivision_id)
    
    # Verificar si hay parcelas asociadas
    parcelas_asociadas = Parcela.objects.filter(subdivision=sub.nombre) | Parcela.objects.filter(subdivision_ref=sub)
    if parcelas_asociadas.exists():
        raise HttpError(400, f"No se puede eliminar la subdivisión '{sub.nombre}' porque existen parcelas asociadas a ella.")

    sub.delete()
    return 200, {"success": True, "message": f"Subdivisión '{sub.nombre}' eliminada con éxito."}
