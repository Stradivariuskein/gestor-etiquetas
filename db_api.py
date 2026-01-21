from sqlalchemy import create_engine, Column, Integer, String, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


# --- CONFIGURACIÓN INICIAL ---
Base = declarative_base()

class Etiqueta(Base):
    """Modelo de la tabla etiquetas"""
    __tablename__ = 'etiquetas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    carpeta = Column(String)
    articulo = Column(String)
    medida = Column(String)
    cantidad = Column(Integer)

    def __repr__(self):
        return f"ID: {self.id} | Art: {self.articulo} | Med: {self.medida} | Cant: {self.cantidad}"

# --- CLASE DE GESTIÓN (INTERFAZ) ---
class EtiquetaManager:
    def __init__(self, db_path_param="etiquetas.db"):
        db_path = f"sqlite:///{db_path_param}"
        self.engine = create_engine(db_path, echo=False)
        Base.metadata.create_all(self.engine) # Crea la tabla si no existe
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    # 1. LISTAR
    def listar_todas(self):
        """Devuelve todas las etiquetas en la base de datos."""
        print(f"listando todas") #borrar
        return self.session.query(Etiqueta).all()

    # 2. CREAR
    def crear(self, articulo, medida, cantidad, carpeta=""):
        """Crea y guarda una nueva etiqueta."""
        print("creando etiqueta")#borrar
        if carpeta:
            medida_pat_1 = medida.lower().split("x")[0].replace("/","-").strip()
            new_carpeta = f"{carpeta}\\{medida_pat_1}"
        nueva = Etiqueta(articulo=articulo, medida=medida, cantidad=cantidad, carpeta=new_carpeta)
        self.session.add(nueva)
        self.session.commit()
        return nueva

    # 3. BUSCAR
    def buscar_por_texto(self, termino):
        """Busca coincidencias en artículo, medida o carpeta (path)."""
        print("buscando etiqueta")#borrar
        termino_search = f"%{termino}%"
        return self.session.query(Etiqueta).filter(
            or_(
                Etiqueta.articulo.like(termino_search),
                Etiqueta.medida.like(termino_search),
                Etiqueta.carpeta.like(termino_search)  # Nueva condición para el path
            )
        ).all()

    def obtener_por_id(self, etiqueta_id):
        """Busca una etiqueta específica por su ID usando el estilo SQLAlchemy 2.0."""
        return self.session.get(Etiqueta, etiqueta_id)
    # 4. MODIFICAR
    def modificar(self, etiqueta_id, **kwargs):
        """
        Modifica campos específicos. 
        Uso: manager.modificar(1, cantidad=500, medida='1/2')
        """
        etiqueta = self.obtener_por_id(etiqueta_id)
        if etiqueta:
            for clave, valor in kwargs.items():
                if hasattr(etiqueta, clave):
                    setattr(etiqueta, clave, valor)
            self.session.commit()
            return True
        return False

    # 5. ELIMINAR
    def eliminar(self, etiqueta_id):
        """Borra una etiqueta por su ID."""
        etiqueta = self.obtener_por_id(etiqueta_id)
        if etiqueta:
            self.session.delete(etiqueta)
            self.session.commit()
            return True
        return False

    def cerrar(self):
        """Cierra la conexión de la sesión."""
        self.session.close()

# --- EJEMPLO DE USO ---
if __name__ == "__main__":
    manager = EtiquetaManager()

    print("--- 1. Creando una etiqueta de prueba ---")
    nueva_etiqueta = manager.crear("ARANDELAS CHAPISTA", "3/4", 5, "ARANDELAS/CHAPISTA")

    print("\n--- 2. Listando todas las etiquetas ---")
    for e in manager.listar_todas()[:5]: # Mostramos las primeras 5
        print(e)

    print("\n--- 3. Buscando 'WHITWORTH' ---")
    resultados = manager.buscar_por_texto("WHITWORTH")
    for r in resultados:
        print(r)

    print(f"\n--- 4. Modificando cantidad de la etiqueta ID {nueva_etiqueta.id} ---")
    if manager.modificar(nueva_etiqueta.id, cantidad=999):
        print("Modificado con éxito:", manager.obtener_por_id(nueva_etiqueta.id))

    print(f"\n--- 5. Eliminando la etiqueta ID {nueva_etiqueta.id} ---")
    if manager.eliminar(nueva_etiqueta.id):
        print(f"Etiqueta ID {nueva_etiqueta.id} eliminada.")

