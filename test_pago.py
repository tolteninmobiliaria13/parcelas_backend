import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parcelas_backend.settings')
django.setup()

import uuid, traceback
from api.models import Pago
from datetime import date

SPANISH_MONTHS = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}

try:
    pago = Pago.objects.get(id=uuid.UUID('99acc79f-2762-45f0-8ae6-9030b9214750'))
    month_name = SPANISH_MONTHS.get(pago.fecha_vencimiento.month, 'Enero')
    days_overdue = None

    # Simulate the same logic as actualizar_pago
    p_estado = pago.estado
    p_fecha_vencimiento = pago.fecha_vencimiento

    if p_estado == 'pendiente' and p_fecha_vencimiento < date.today():
        p_estado = 'vencido'

    if p_estado == 'vencido':
        delta = date.today() - p_fecha_vencimiento
        days_overdue = max(delta.days, 0)

    receipt = None
    if p_estado == 'pagado':
        receipt = 'REC-{}-{}'.format(p_fecha_vencimiento.year, pago.id.hex[:4].upper())

    data = {
        'id': str(pago.id),
        'month': month_name,
        'year': p_fecha_vencimiento.year,
        'status': p_estado,
        'amount': float(pago.monto_cobrar),
        'dueDate': p_fecha_vencimiento.strftime('%d/%m/%Y'),
        'paidDate': pago.fecha_pago_real.strftime('%d/%m/%Y') if pago.fecha_pago_real else None,
        'receiptNumber': receipt,
        'daysOverdue': days_overdue
    }
    print('Response dict OK:')
    for k, v in data.items():
        print(f'  {k}: {v!r}')

except Exception as e:
    traceback.print_exc()
