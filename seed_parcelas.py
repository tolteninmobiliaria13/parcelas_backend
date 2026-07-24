import os
import django

# Inicializar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parcelas_backend.settings')
django.setup()

from api.models import Parcela

# Definición de parcelas
LOTES_PRIMERA = [
    ("A-1", 25000000.0),
    ("A-2", 25000000.0),
    ("A-3", 17000028.0),
    ("A-4", 17000000.0),
    ("A-5", 88000000.0),
    ("A-6", 17000000.0),
    ("A-7", 0.0),
    ("A-8", 0.0),
    ("A-9", 0.0),
    ("A-10", 17000000.0),
    ("A-11", 17000000.0),
    ("A-12", 15000000.0),
    ("A-13", 12000000.0),
    ("A-14", 17000000.0),
    ("A-15", 0.0),
    ("A-16", 17000000.0),
    ("A-17", 20000000.0),
    ("A-18", 19000000.0),
    ("A-19", 0.0),
    ("A-20", 0.0),
    ("A-21", 20000000.0),
    ("A-22", 25000000.0),
    ("A-23", 25000000.0),
    ("A-24", 17000000.0),
    ("A-25", 17000000.0),
    ("A-26", 12000000.0),
    ("A-27", 12000000.0),
    ("A-28", 22000000.0),
    ("A-29", 22000000.0),
    ("A-30", 33000000.0),
    ("A-31", 0.0),
    ("A-32", 0.0),
    ("a-1", 20000000.0),
]

LOTES_SUBDIVISION_3 = [
    ("A-32-A", 22000000.0),
    ("A-32-B", 16000000.0),
    ("A-32-C", 20000000.0),
    ("A-32-D", 16000000.0),
    ("A-32-E", 25000000.0),
    ("A-32-F", 16000000.0),
    ("A-32-G", 16000000.0),
    ("A-32-H", 16000000.0),
    ("A-32-I", 15000000.0),
    ("A-32-J", 25000000.0),
    ("A-32-K", 16000000.0),
    ("A-32-L", 25000000.0),
    ("A-32-M", 20000000.0),
    ("A-32-N", 20000000.0),
    ("A-32-Ñ", 14000000.0),
    ("A-32-O", 20000000.0),
    ("A-32-P", 15000000.0),
    ("A-32-Q", 15000000.0),
    ("A-32-R", 0.0),
    ("A-32-S", 16000000.0),
    ("A-32-T", 0.0),
    ("A-32-U", 0.0),
    ("A-32-V", 10000000.0),
    ("A-32-W", 10000000.0),
    ("A-32-X", 11000000.0),
    ("A-32-Y", 11000000.0),
    ("A-32-Z", 0.0),
    ("A-32-Z1", 0.0),
    ("A-32-Z2", 0.0),
    ("A-32-Z3", 16000000.0),
]

def seed():
    creados = 0
    actualizados = 0

    print("--- Procesando Subdivisión Primera ---")
    for lote, precio in LOTES_PRIMERA:
        parcela, created = Parcela.objects.update_or_create(
            numero_lote=lote,
            defaults={
                'subdivision': 'primera',
                'precio_base': precio,
            }
        )
        if created:
            creados += 1
            print(f"[NUEVA PARCELA] {lote} (subdivisión: primera, precio: ${precio:,.0f})")
        else:
            actualizados += 1
            print(f"[ACTUALIZADA PARCELA] {lote} (subdivisión: primera, precio: ${precio:,.0f})")

    print("\n--- Procesando Subdivisión 3 ---")
    for lote, precio in LOTES_SUBDIVISION_3:
        parcela, created = Parcela.objects.update_or_create(
            numero_lote=lote,
            defaults={
                'subdivision': 'subdivision 3',
                'precio_base': precio,
            }
        )
        if created:
            creados += 1
            print(f"[NUEVA PARCELA] {lote} (subdivisión: subdivision 3, precio: ${precio:,.0f})")
        else:
            actualizados += 1
            print(f"[ACTUALIZADA PARCELA] {lote} (subdivisión: subdivision 3, precio: ${precio:,.0f})")

    print(f"\n--- Resumen Final de Carga de Parcelas ---")
    print(f"Parcelas creadas: {creados}")
    print(f"Parcelas actualizadas: {actualizados}")
    print(f"Total procesadas: {creados + actualizados}")

if __name__ == '__main__':
    seed()
