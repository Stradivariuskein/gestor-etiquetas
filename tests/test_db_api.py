import unittest
from db_api import EtiquetaManager, Etiqueta
import sys
import os

# Añade la carpeta raíz al camino de búsqueda de Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestEtiquetaManager(unittest.TestCase):
    
    def setUp(self):
        """
        Se ejecuta ANTES de cada test. 
        Usamos ':memory:' para crear una DB temporal en RAM que se borra al terminar.
        """
        # Al pasar ":memory:", SQLAlchemy crea la DB en la RAM.
        # Nota: En tu clase original db_api.py, se concatena "sqlite:///" + path.
        # Por lo tanto pasamos ":memory:" para que quede "sqlite:///:memory:"
        self.manager = EtiquetaManager(db_path_param=":memory:")

    def tearDown(self):
        """Se ejecuta DESPUÉS de cada test."""
        self.manager.cerrar()

    def test_crear_etiqueta_simple(self):
        """Prueba la creación básica de una etiqueta."""
        etiqueta = self.manager.crear(
            articulo="TORNILLO", 
            medida="1/2", 
            cantidad=100, 
            carpeta="TORNILLOS"
        )
        
        self.assertIsNotNone(etiqueta.id, "El ID no debería ser None después de guardar")
        self.assertEqual(etiqueta.articulo, "TORNILLO")
        self.assertEqual(etiqueta.cantidad, 100)

        # Verificar que se guardó en DB consultando de nuevo
        en_db = self.manager.obtener_por_id(etiqueta.id)
        self.assertEqual(en_db.articulo, "TORNILLO")

    def test_logica_carpeta_path(self):
        """
        Prueba la lógica específica de formateo de carpetas en el método crear.
        Tu código hace: medida.lower().split("x")[0].replace("/","-").strip()
        """
        # Caso 1: Medida con barra "/" debe cambiarse a "-"
        etiqueta = self.manager.crear("ARANDELA", "1/2", 50, "BASE")
        # Esperado: BASE\1-2
        expected_path = "BASE\\1-2"
        self.assertEqual(etiqueta.carpeta, expected_path)

        # Caso 2: Medida con "x" (ej: 10x50), debe tomar solo la primera parte
        etiqueta2 = self.manager.crear("BULON", "10x50", 20, "BASE")
        # Esperado: BASE\10
        expected_path_2 = "BASE\\10"
        self.assertEqual(etiqueta2.carpeta, expected_path_2)

    def test_listar_todas(self):
        """Prueba que se listan todos los elementos."""
        self.manager.crear("A", "1", 10)
        self.manager.crear("B", "2", 20)
        
        lista = self.manager.listar_todas()
        self.assertEqual(len(lista), 2)

    def test_buscar_por_texto(self):
        """Prueba el filtrado por texto (Articulo, Medida o Carpeta)."""
        self.manager.crear("TORNILLO HEX", "1/4", 100, "CAJA_A")
        self.manager.crear("ARANDELA PLANA", "1/4", 200, "CAJA_B")
        self.manager.crear("TUERCA", "5/8", 50, "CAJA_A")

        # 1. Buscar por nombre parcial ("HEX")
        res_hex = self.manager.buscar_por_texto("HEX")
        self.assertEqual(len(res_hex), 1)
        self.assertEqual(res_hex[0].articulo, "TORNILLO HEX")

        # 2. Buscar por medida ("1/4") -> Debería traer Tornillo y Arandela
        res_medida = self.manager.buscar_por_texto("1/4")
        self.assertEqual(len(res_medida), 2)

        # 3. Buscar por carpeta ("CAJA_A") -> Tornillo y Tuerca (la carpeta se guarda en el path)
        # Nota: Tu metodo 'crear' modifica la carpeta añadiendo la medida.
        # TORNILLO -> CAJA_A\1-4
        # TUERCA -> CAJA_A\5-8
        res_carpeta = self.manager.buscar_por_texto("CAJA_A")
        self.assertEqual(len(res_carpeta), 2)

    def test_modificar_etiqueta(self):
        """Prueba la actualización de campos."""
        etiqueta = self.manager.crear("TEST", "10", 10)
        
        # Modificar cantidad y medida
        exito = self.manager.modificar(etiqueta.id, cantidad=999, medida="20")
        
        self.assertTrue(exito)
        
        # Recuperar de DB para asegurar persistencia
        actualizado = self.manager.obtener_por_id(etiqueta.id)
        self.assertEqual(actualizado.cantidad, 999)
        self.assertEqual(actualizado.medida, "20")
        # El artículo no debió cambiar
        self.assertEqual(actualizado.articulo, "TEST")

    def test_modificar_id_inexistente(self):
        """Prueba modificar un ID que no existe."""
        exito = self.manager.modificar(9999, cantidad=50)
        self.assertFalse(exito)

    def test_eliminar_etiqueta(self):
        """Prueba borrar una etiqueta."""
        etiqueta = self.manager.crear("BORRAR", "1", 1)
        id_borrar = etiqueta.id
        
        # Eliminar
        exito = self.manager.eliminar(id_borrar)
        self.assertTrue(exito)
        
        # Verificar que ya no existe
        busqueda = self.manager.obtener_por_id(id_borrar)
        self.assertIsNone(busqueda)

    def test_eliminar_id_inexistente(self):
        """Prueba eliminar un ID que no existe."""
        exito = self.manager.eliminar(9999)
        self.assertFalse(exito)

if __name__ == '__main__':
    unittest.main()