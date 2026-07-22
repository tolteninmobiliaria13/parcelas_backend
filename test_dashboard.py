import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parcelas_backend.settings')
django.setup()

from datetime import date
from django.db.models import Sum
from api.models import Pago

today = date.today()
qs = Pago.objects.filter(
    estado__in=['pendiente', 'vencido'],
    fecha_vencimiento__year=today.year,
    fecha_vencimiento__month=today.month,
)
result = qs.aggregate(total=Sum('monto_cobrar'))
count = qs.count()
print(f"Mes: {today.month}/{today.year}")
print(f"Cuotas sin pagar este mes: {count}")
print(f"Total a pagar: ${result['total'] or 0:,.0f}")
