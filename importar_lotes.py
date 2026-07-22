import os
import django

# Inicializar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parcelas_backend.settings')
django.setup()

from api.models import Parcela

raw_data = """
A-1	JOSE ANGEL RIOS ARIAS (Sofía)	$25.000.000	$2.500.000	$22.500.000	$1.111.111	X		35	$611.111	05/01/2025
A-2	MADELINE ADRIANA SAEZ VARELA (Sofía)	$25.000.000	$5.000.000	$20.000.000		x		36	$555.555	05/01/2025
A-3	MARJORIE ELIZETTE CHAVEZ SILVA	$17.000.028	$472.223	$16.527.805		X		35	$472.223	30/03/2024
A-4	CLARA LETICIA MUÑOZ MUÑOZ	$17.000.000	$5.000.000	$12.000.000		X		36	$333.333	30/05/2024
A-5	JULIO ANDRES CABRERA GOMEZ	$88.000.000	$65.000.000	$23.000.000		x		1		29/12/2024
A-6	MISAEL JUSTO PALMA LILLO	$17.000.000	$17.000.000	$0						
A-7	Toro Lillo									
A-8	Toro Lillo									
A-9	Toro Lillo									
A-10	MARITZA ANDREA REYES MOYA	$17.000.000	$5.000.000	$12.000.000		X		36	$333.333	29/03/2024
A-11	MARCELA DEL PILAR MOYA SANCHEZ	$17.000.000	$5.000.000	$12.000.000		X		36	$333.333	29/03/2024
A-12	EDUARDO ANDRES SILVA SAAVEDRA	$15.000.000	$2.000.000	$13.000.000		X		36	$361.111	30/07/2024
A-13	JENNIFER NATALY SILVA SAAVEDRA	$12.000.000	$4.000.000	$8.000.000		X				
A-14	GUACOLDA DE LOS ANGELES MOYA SANCHEZ	$17.000.000	$8.000.000	$9.000.000		X		36	$250.000	30/04/2025
A-15	Toro Lillo									
A-16	CLAUDIO ANDRES HORTSMEIER FERREIRA (Sofía) 	$17.000.000	$5.000.000	$12.000.000		x		36	$333.333	10/02/2025
A-17	SOFIA INES JARAMILLO LEFICURA (Sofía)	$20.000.000	$2.000.000	$18.000.000		X		24	$750.000	30/01/2025
A-18	MIX DE AVENTURAS SpA	$19.000.000	$3.000.000	$16.000.000		X		36	$444.444	30/08/2025
A-19	EMILIO POBLETE									
A-20	EMILIO POBLETE									
A-21	JUAN CARLOS BERMUDEZ	$20.000.000	$5.000.000	$15.000.000		X				$350.000 30/10/2025
A-22	ANGELO AMERICO MADARIAGA YAÑEZ	$25.000.000	$5.000.000	$20.000.000		X		48	$416.667	22/03/2024
A-23	DAVID MARCIAL MADARIAGA YAÑEZ	$25.000.000	$5.000.000	$20.000.000		X		48	$416.667	22/03/2024
A-24	ORIANA DEL PILAR MORALES GALAN	$17.000.000	$17.000.000	$0			X			
A-25	ROBERTO ANTONIO JOPIA STUBING	$17.000.000	$17.000.000	$0			X			
A-26	ANSELMO HUMBERTO URRA BARRERA	$12.000.000	$12.000.000	$0			X			
A-27	ANSELMO HUMBERTO URRA BARRERA	$12.000.000	$12.000.000	$0			X			
A-28	JULIO ANDRES CABRERA GOMEZ	$22.000.000	$10.000.000	$12.000.000		X		1	$12.000.000	
A-29	JULIO ANDRES CABRERA GOMEZ	$22.000.000	$10.000.000	$12.000.000		X		1	$12.000.000	
A-30	FRANCISCA DAHILYN PINEDA ARANEDA	$33.000.000	$5.000.000	$28.000.000		X		36	$777.777	06/11/2025
A-31	PERMUTA									
A-32	PERMUTA									
a-1	NILSA BERTA MELLA FERNANDEZ	$20.000.000	$5.000.000	$15.000.000		X		36	$416.666	30/07/2025
"""

lines = [l.strip() for l in raw_data.strip().split('\n') if l.strip()]

creados = 0
for line in lines:
    parts = line.split('\t')
    if not parts:
        continue
    
    lote_num = parts[0].strip()
    comprador = parts[1].strip() if len(parts) > 1 else ""
    
    # Limpieza de precio de venta
    precio_str = parts[2].strip() if len(parts) > 2 else ""
    if precio_str:
        precio_val = precio_str.replace('$', '').replace('.', '').replace(' ', '').strip()
        precio_base = float(precio_val) if precio_val else 0.0
    else:
        precio_base = 0.0

    # Determinación de estado
    if comprador:
        estado = 'vendida'
    else:
        estado = 'disponible'

    # Se inserta o actualiza la parcela
    parcela, created = Parcela.objects.update_or_create(
        numero_lote=lote_num,
        defaults={
            'subdivision': 'primera',
            'superficie_m2': None,
            'precio_base': precio_base,
            'estado': estado
        }
    )
    
    if created:
        creados += 1
        print(f"[NUEVO] Lote {lote_num} -> subdivisión: primera, precio: ${precio_base:.0f}, estado: {estado}")
    else:
        print(f"[ACTUALIZADO] Lote {lote_num} -> subdivisión: primera, precio: ${precio_base:.0f}, estado: {estado}")

print(f"\nImportación finalizada. Se crearon {creados} lotes nuevos.")
