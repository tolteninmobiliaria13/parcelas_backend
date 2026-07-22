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