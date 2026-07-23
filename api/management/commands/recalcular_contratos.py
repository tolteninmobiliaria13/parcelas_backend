from django.core.management.base import BaseCommand
from api.models import Contrato, recalcular_contrato

class Command(BaseCommand):
    help = 'Recalcula los campos cacheados de todos los contratos existentes'

    def handle(self, *args, **kwargs):
        contratos = Contrato.objects.all()
        total = contratos.count()
        self.stdout.write(f"Iniciando recálculo de {total} contratos...")
        
        for i, contrato in enumerate(contratos, 1):
            recalcular_contrato(contrato.id)
            if i % 10 == 0:
                self.stdout.write(f"Progreso: {i}/{total}")
                
        self.stdout.write(self.style.SUCCESS("Recálculo completado exitosamente."))
