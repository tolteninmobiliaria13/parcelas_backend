import os
import django

# Inicializar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parcelas_backend.settings')
django.setup()

from api.models import Cliente

NOMBRES_CLIENTES = [
    "JOSE ANGEL RIOS ARIAS (Sofía)",
    "MADELINE ADRIANA SAEZ VARELA (Sofía)",
    "MARJORIE ELIZETTE CHAVEZ SILVA",
    "CLARA LETICIA MUÑOZ MUÑOZ",
    "JULIO ANDRES CABRERA GOMEZ",
    "MISAEL JUSTO PALMA LILLO",
    "Toro Lillo",
    "MARITZA ANDREA REYES MOYA",
    "MARCELA DEL PILAR MOYA SANCHEZ",
    "EDUARDO ANDRES SILVA SAAVEDRA",
    "JENNIFER NATALY SILVA SAAVEDRA",
    "GUACOLDA DE LOS ANGELES MOYA SANCHEZ",
    "CLAUDIO ANDRES HORTSMEIER FERREIRA (Sofía)",
    "SOFIA INES JARAMILLO LEFICURA (Sofía)",
    "MIX DE AVENTURAS SpA",
    "EMILIO POBLETE",
    "JUAN CARLOS BERMUDEZ",
    "ANGELO AMERICO MADARIAGA YAÑEZ",
    "DAVID MARCIAL MADARIAGA YAÑEZ",
    "ORIANA DEL PILAR MORALES GALAN",
    "ROBERTO ANTONIO JOPIA STUBING",
    "ANSELMO HUMBERTO URRA BARRERA",
    "FRANCISCA DAHILYN PINEDA ARANEDA",
    "NILSA BERTA MELLA FERNANDEZ",
    "SARA INES ACEITUNO QUILODRAN",
    "XIMENA ACEITUNO QUILODRAN",
    "PATRICIA SOLEDAD CANIUQUEO PENCHULEF",
    "LUZ MARIA BRAVO DURAN",
    "CRISTOFER ANDRES CAVIERES ARANEDA",
    "HERNAN ALEJANDRO GALVEZ BETANCOUR",
    "CAMILA ALEJANDRA SANCHEZ ARANEDA",
    "WALTER GUILLERMO JARA MUÑOZ",
    "CARMEN ROSA CASTILLO PINTO",
    "GLADIS ISABEL BELMAR",
    "RICARDO RODRIGO MUÑOZ VIDAL",
    "CECILIA DEL CARMEN VALLEJOS OSSES",
    "MAURICIO ANDRES MONSALVEZ MELLA",
    "JUAN ELISEO VALDEVENITO FUENTES",
    "ANDREA DEL CARMEN GONZALEZ HERRERA",
    "PABLO CIFUENTES BEAMIN",
    "NELSON ABEL PAREDES CEBALLOS",
    "SILVIA VIVIANA PAREDES CEBALLOS",
    "ANA LUZ CRUCES PESO"
]

def seed():
    creados = 0
    existentes = 0
    
    for nombre in NOMBRES_CLIENTES:
        nombre_clean = nombre.strip()
        if not nombre_clean:
            continue

        cliente, created = Cliente.objects.get_or_create(
            nombre_completo=nombre_clean
        )

        if created:
            creados += 1
            print(f"[NUEVO CLIENTE] -> {nombre_clean}")
        else:
            existentes += 1
            print(f"[EXISTENTE] -> {nombre_clean}")

    print(f"\n--- Resumen de Carga Masiva de Clientes ---")
    print(f"Clientes nuevos creados: {creados}")
    print(f"Clientes previamente existentes: {existentes}")
    print(f"Total procesados: {creados + existentes}")

if __name__ == '__main__':
    seed()
