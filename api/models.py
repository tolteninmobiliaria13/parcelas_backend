import uuid
from django.db import models

#cada clase indica una tabla de la base de datos
class Cliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre_completo = models.CharField(max_length=255)
    # email ahora permite nulos
    email = models.EmailField(null=True, blank=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre_completo

    class Meta:
        db_table = 'clientes'

class Parcela(models.Model):
    ESTADO_CHOICES = [
        ('disponible', 'Disponible'),
        ('reservada', 'Reservada'),
        ('vendida', 'Vendida'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero_lote = models.CharField(max_length=50)
    # numero_rol y superficie_m2 ahora permiten nulos
    numero_rol = models.CharField(max_length=50, null=True, blank=True)
    subdivision = models.CharField(max_length=100)
    superficie_m2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_base = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='disponible')

    def __str__(self):
        return f"{self.numero_lote} - {self.subdivision}"

    class Meta:
        db_table = 'parcelas'

class Contrato(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('finalizado', 'Finalizado'),
        ('incumplido', 'Incumplido'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.RESTRICT)
    parcela = models.ForeignKey(Parcela, on_delete=models.RESTRICT)
    fecha_pago = models.DateField()
    pie_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    total_cuotas = models.IntegerField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')

    # Nuevos campos cacheados
    saldo_pendiente = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    proximo_vencimiento = models.DateField(null=True, blank=True)
    ultimo_pago = models.DateField(null=True, blank=True)
    estado_calculado = models.CharField(max_length=20, choices=[('current', 'Current'), ('overdue', 'Overdue'), ('inactive', 'Inactive')], default='inactive')
    installment_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Contrato {self.id} - {self.cliente.nombre_completo}"

    class Meta:
        db_table = 'contratos'

class Pago(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('vencido', 'Vencido'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='pagos')
    numero_cuota = models.IntegerField()
    monto_cobrar = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_vencimiento = models.DateField()
    fecha_pago_real = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    def __str__(self):
        return f"Cuota {self.numero_cuota} - Contrato {self.contrato.id}"

    class Meta:
        db_table = 'pagos'

# --- Signal y Helper de Recálculo ---
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, Min, Max

def recalcular_contrato(contrato_id):
    pagos = Pago.objects.filter(contrato_id=contrato_id)
    if not pagos.exists():
        Contrato.objects.filter(id=contrato_id).update(
            saldo_pendiente=0,
            proximo_vencimiento=None,
            ultimo_pago=None,
            estado_calculado='inactive',
            installment_value=0
        )
        return

    # Saldo de cuotas pendientes o vencidas
    saldo = pagos.exclude(estado='pagado').aggregate(t=Sum('monto_cobrar'))['t'] or 0
    
    # Próximo vencimiento
    proximo = pagos.exclude(estado='pagado').aggregate(m=Min('fecha_vencimiento'))['m']
    
    # Último pago
    ultimo = pagos.filter(estado='pagado').aggregate(m=Max('fecha_pago_real'))['m']
    
    # Monto de primera cuota para "installment_value"
    primera_cuota = pagos.order_by('numero_cuota').first()
    inst_val = primera_cuota.monto_cobrar if primera_cuota else 0

    # Determinar estado
    vencidos = pagos.filter(estado='vencido').count()
    pendientes = pagos.exclude(estado='pagado').count()
    if vencidos > 0:
        estado_calc = 'overdue'
    elif pendientes > 0:
        estado_calc = 'current'
    else:
        estado_calc = 'inactive'

    Contrato.objects.filter(id=contrato_id).update(
        saldo_pendiente=saldo,
        proximo_vencimiento=proximo,
        ultimo_pago=ultimo,
        estado_calculado=estado_calc,
        installment_value=inst_val
    )

@receiver(post_save, sender=Pago)
@receiver(post_delete, sender=Pago)
def update_contrato_cache(sender, instance, **kwargs):
    recalcular_contrato(instance.contrato_id)