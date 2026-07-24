import os
import django
from datetime import datetime, date

# Inicializar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parcelas_backend.settings')
django.setup()

from api.models import Cliente, Parcela, Contrato, Pago

def add_months(sourcedate: date, months: int) -> date:
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    max_days = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    day = min(sourcedate.day, max_days)
    return date(year, month, day)

RAW_CONTRATOS = [
    # (lote, comprador, precio_venta, abono, saldo, total_cuotas, valor_cuota, fecha_vencimiento_str)
    ("A-1", "JOSE ANGEL RIOS ARIAS (Sofía)", 25000000.0, 2500000.0, 22500000.0, 35, 611111.0, "2025-01-05"),
    ("A-2", "MADELINE ADRIANA SAEZ VARELA (Sofía)", 25000000.0, 5000000.0, 20000000.0, 36, 555555.0, "2025-01-05"),
    ("A-3", "MARJORIE ELIZETTE CHAVEZ SILVA", 17000028.0, 472223.0, 16527805.0, 35, 472223.0, "2024-03-30"),
    ("A-4", "CLARA LETICIA MUÑOZ MUÑOZ", 17000000.0, 5000000.0, 12000000.0, 36, 333333.0, "2024-05-30"),
    ("A-5", "JULIO ANDRES CABRERA GOMEZ", 88000000.0, 65000000.0, 23000000.0, 1, 23000000.0, "2024-12-29"),
    ("A-6", "MISAEL JUSTO PALMA LILLO", 17000000.0, 17000000.0, 0.0, 0, 0.0, None),
    ("A-10", "MARITZA ANDREA REYES MOYA", 17000000.0, 5000000.0, 12000000.0, 36, 333333.0, "2024-03-29"),
    ("A-11", "MARCELA DEL PILAR MOYA SANCHEZ", 17000000.0, 5000000.0, 12000000.0, 36, 333333.0, "2024-03-29"),
    ("A-12", "EDUARDO ANDRES SILVA SAAVEDRA", 15000000.0, 2000000.0, 13000000.0, 36, 361111.0, "2024-07-30"),
    ("A-13", "JENNIFER NATALY SILVA SAAVEDRA", 12000000.0, 4000000.0, 8000000.0, 0, 0.0, None),
    ("A-14", "GUACOLDA DE LOS ANGELES MOYA SANCHEZ", 17000000.0, 8000000.0, 9000000.0, 36, 250000.0, "2025-04-30"),
    ("A-16", "CLAUDIO ANDRES HORTSMEIER FERREIRA (Sofía)", 17000000.0, 5000000.0, 12000000.0, 36, 333333.0, "2025-02-10"),
    ("A-17", "SOFIA INES JARAMILLO LEFICURA (Sofía)", 20000000.0, 2000000.0, 18000000.0, 24, 750000.0, "2025-01-30"),
    ("A-18", "MIX DE AVENTURAS SpA", 19000000.0, 3000000.0, 16000000.0, 36, 444444.0, "2025-08-30"),
    ("A-21", "JUAN CARLOS BERMUDEZ", 20000000.0, 5000000.0, 15000000.0, 0, 350000.0, "2025-10-30"),
    ("A-22", "ANGELO AMERICO MADARIAGA YAÑEZ", 25000000.0, 5000000.0, 20000000.0, 48, 416667.0, "2024-03-22"),
    ("A-23", "DAVID MARCIAL MADARIAGA YAÑEZ", 25000000.0, 5000000.0, 20000000.0, 48, 416667.0, "2024-03-22"),
    ("A-24", "ORIANA DEL PILAR MORALES GALAN", 17000000.0, 17000000.0, 0.0, 0, 0.0, None),
    ("A-25", "ROBERTO ANTONIO JOPIA STUBING", 17000000.0, 17000000.0, 0.0, 0, 0.0, None),
    ("A-26", "ANSELMO HUMBERTO URRA BARRERA", 12000000.0, 12000000.0, 0.0, 0, 0.0, None),
    ("A-27", "ANSELMO HUMBERTO URRA BARRERA", 12000000.0, 12000000.0, 0.0, 0, 0.0, None),
    ("A-28", "JULIO ANDRES CABRERA GOMEZ", 22000000.0, 10000000.0, 12000000.0, 1, 12000000.0, None),
    ("A-29", "JULIO ANDRES CABRERA GOMEZ", 22000000.0, 10000000.0, 12000000.0, 1, 12000000.0, None),
    ("A-30", "FRANCISCA DAHILYN PINEDA ARANEDA", 33000000.0, 5000000.0, 28000000.0, 36, 777777.0, "2025-11-06"),
    ("a-1", "NILSA BERTA MELLA FERNANDEZ", 20000000.0, 5000000.0, 15000000.0, 36, 416666.0, "2025-07-30"),

    # Subdivisión 3 (A-32-*)
    ("A-32-A", "SARA INES ACEITUNO QUILODRAN", 22000000.0, 4000000.0, 18000000.0, 36, 500000.0, "2025-11-30"),
    ("A-32-B", "XIMENA ACEITUNO QUILODRAN", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
    ("A-32-C", "PATRICIA SOLEDAD CANIUQUEO PENCHULEF", 20000000.0, 7000000.0, 13000000.0, 36, 361111.0, "2025-12-06"),
    ("A-32-D", "LUZ MARIA BRAVO DURAN", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
    ("A-32-E", "CRISTOFER ANDRES CAVIERES ARANEDA", 25000000.0, 5000000.0, 20000000.0, 36, 555555.0, "2026-01-06"),
    ("A-32-F", "HERNAN ALEJANDRO GALVEZ BETANCOUR", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
    ("A-32-G", "CAMILA ALEJANDRA SANCHEZ ARANEDA", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
    ("A-32-H", "WALTER GUILLERMO JARA MUÑOZ", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
    ("A-32-I", "CARMEN ROSA CASTILLO PINTO", 15000000.0, 15000000.0, 0.0, 0, 0.0, None),
    ("A-32-J", "GLADIS ISABEL BELMAR", 25000000.0, 5000000.0, 20000000.0, 48, 416698.0, "2026-04-10"),
    ("A-32-K", "RICARDO RODRIGO MUÑOZ VIDAL", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
    ("A-32-L", "CECILIA DEL CARMEN VALLEJOS OSSES", 25000000.0, 5000000.0, 20000000.0, 36, 555555.0, "2026-02-05"),
    ("A-32-M", "MAURICIO ANDRES MONSALVEZ MELLA", 20000000.0, 5000000.0, 15000000.0, 30, 500000.0, "2025-12-10"),
    ("A-32-N", "MAURICIO ANDRES MONSALVEZ MELLA", 20000000.0, 5000000.0, 15000000.0, 30, 500000.0, "2025-12-10"),
    ("A-32-Ñ", "JUAN ELISEO VALDEVENITO FUENTES", 14000000.0, 14000000.0, 0.0, 0, 0.0, None),
    ("A-32-O", "MAURICIO ANDRES MONSALVEZ MELLA", 20000000.0, 0.0, 20000000.0, 48, 416666.0, "2026-02-24"),
    ("A-32-P", "ANDREA DEL CARMEN GONZALEZ HERRERA", 15000000.0, 15000000.0, 0.0, 0, 0.0, None),
    ("A-32-Q", "ANDREA DEL CARMEN GONZALEZ HERRERA", 15000000.0, 15000000.0, 0.0, 0, 0.0, None),
    ("A-32-S", "PABLO CIFUENTES BEAMIN", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
    ("A-32-V", "NELSON ABEL PAREDES CEBALLOS", 10000000.0, 10000000.0, 0.0, 0, 0.0, None),
    ("A-32-W", "NELSON ABEL PAREDES CEBALLOS", 10000000.0, 10000000.0, 0.0, 0, 0.0, None),
    ("A-32-X", "SILVIA VIVIANA PAREDES CEBALLOS", 11000000.0, 11000000.0, 0.0, 0, 0.0, None),
    ("A-32-Y", "SILVIA VIVIANA PAREDES CEBALLOS", 11000000.0, 11000000.0, 0.0, 0, 0.0, None),
    ("A-32-Z3", "ANA LUZ CRUCES PESO", 16000000.0, 16000000.0, 0.0, 0, 0.0, None),
]

def seed():
    creados = 0
    actualizados = 0
    cuotas_creadas = 0

    today = date.today()

    for item in RAW_CONTRATOS:
        lote_num, comprador_nombre, precio_venta, abono, saldo, cant_cuotas, valor_cuota, venc_str = item

        # 1. Buscar Cliente
        try:
            cliente = Cliente.objects.get(nombre_completo__iexact=comprador_nombre.strip())
        except Cliente.DoesNotExist:
            print(f"[ERROR] Cliente no encontrado: '{comprador_nombre}'")
            continue

        # 2. Buscar Parcela con coincidencia exacta de lote para distinguir 'a-1' de 'A-1'
        subdiv_target = "subdivision 3" if lote_num.strip().upper().startswith("A-32-") else "primera"
        parcela = Parcela.objects.filter(numero_lote=lote_num.strip(), subdivision__iexact=subdiv_target).first()
        if not parcela:
            parcela = Parcela.objects.filter(numero_lote=lote_num.strip()).first()
        
        if not parcela:
            print(f"[ERROR] Parcela no encontrada: '{lote_num}' ({subdiv_target})")
            continue

        # 3. Formatear fecha vencimiento inicial
        fecha_venc = None
        if venc_str:
            try:
                fecha_venc = datetime.strptime(venc_str, "%Y-%m-%d").date()
            except ValueError:
                fecha_venc = None

        estado_contrato = 'finalizado' if saldo == 0 else 'activo'
        fecha_pago = fecha_venc or today

        # 4. Crear o actualizar Contrato por parcela
        contrato, created = Contrato.objects.update_or_create(
            parcela=parcela,
            defaults={
                'cliente': cliente,
                'fecha_pago': fecha_pago,
                'pie_inicial': abono,
                'total_cuotas': cant_cuotas,
                'saldo_pendiente': saldo,
                'installment_value': valor_cuota,
                'proximo_vencimiento': fecha_venc,
                'estado': estado_contrato,
            }
        )

        # 5. Marcar Parcela como 'vendida'
        parcela.estado = 'vendida'
        parcela.save()

        if created:
            creados += 1
            print(f"[NUEVO CONTRATO] Lote {parcela.numero_lote} ({parcela.subdivision}) <-> {cliente.nombre_completo} (Cuotas: {cant_cuotas}, Saldo: ${saldo:,.0f})")
        else:
            actualizados += 1
            print(f"[ACTUALIZADO CONTRATO] Lote {parcela.numero_lote} ({parcela.subdivision}) <-> {cliente.nombre_completo}")

        # 6. Generar Cuotas de Pago (Pagos) si aplica
        if cant_cuotas > 0 and valor_cuota > 0 and fecha_venc:
            Pago.objects.filter(contrato=contrato).delete()

            for i in range(1, cant_cuotas + 1):
                venc_cuota = add_months(fecha_venc, i - 1)
                estado_cuota = 'vencido' if venc_cuota < today else 'pendiente'
                
                Pago.objects.create(
                    contrato=contrato,
                    numero_cuota=i,
                    monto_cobrar=valor_cuota,
                    fecha_vencimiento=venc_cuota,
                    estado=estado_cuota
                )
                cuotas_creadas += 1

    print(f"\n--- Resumen Final de Carga de Contratos y Pagos ---")
    print(f"Contratos creados: {creados}")
    print(f"Contratos actualizados: {actualizados}")
    print(f"Cuotas generadas: {cuotas_creadas}")
    print(f"Total contratos procesados: {creados + actualizados}")

if __name__ == '__main__':
    seed()
