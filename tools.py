import sys
import os

def resource_path(relative_path):
    """ Obtiene la ruta absoluta del recurso, compatible con PyInstaller """
    try:
        # PyInstaller crea una carpeta temporal en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_db_path(db_name="etiquetas.db"):
    # Esto obtiene la carpeta donde está el ejecutable (o el script)
    if getattr(sys, 'frozen', False):
        # Si es el .exe, la carpeta es donde está el .exe
        base_dir = os.path.dirname(sys.executable)
    else:
        # Si es el script .py, la carpeta actual
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_dir, db_name)