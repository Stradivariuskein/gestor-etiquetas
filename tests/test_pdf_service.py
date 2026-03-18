import unittest
import os
from unittest.mock import patch, MagicMock, ANY

# Importamos la clase a testear
# Asegúrate de que etiqueta_pdf_service.py esté en la misma carpeta o en el path
from etiqueta_pdf_service import EtiquetaPDFService

class TestEtiquetaPDFService(unittest.TestCase):

    def setUp(self):
        """Se ejecuta antes de cada test. Prepara un entorno limpio."""
        # Mockeamos resource_path para que no falle buscando la imagen real
        with patch('etiqueta_pdf_service.resource_path', return_value="fake_logo.png"):
            self.service = EtiquetaPDFService(base_output="test_output", logo_path="fake_logo.png")

    # ----------------------------------------------------------------
    # 1. TEST DE LÓGICA PURA (Sanitización y Textos)
    # ----------------------------------------------------------------

    def test_safe_filename_elimina_caracteres_prohibidos(self):
        """Verifica que los caracteres ilegales en Windows se reemplacen."""
        nombre_peligroso = 'Tuerca 1/2" x 3\\4'
        resultado = self.service._safe_filename(nombre_peligroso)
        
        # Validamos según la lógica en etiqueta_pdf_service.py
        # "/" -> "_", "\" -> "_", " " -> "_"
        self.assertNotIn('/', resultado)
        self.assertNotIn('\\', resultado)
        self.assertNotIn(' ', resultado)
        self.assertEqual(resultado, 'Tuerca_1_2"_x_3_4')

    def test_partir_en_dos_lineas_balanceado(self):
        """Prueba que el texto se divida correctamente para etiquetas."""
        texto = "ARANDELA PLANA HIERRO ZINCADA" # 4 palabras
        l1, l2 = self.service.partir_en_dos_lineas(texto)
        
        self.assertEqual(l1, "ARANDELA PLANA")
        self.assertEqual(l2, "HIERRO Z.")


    def test_partir_en_dos_lineas_impar(self):
        """Prueba con número impar de palabras."""
        texto = "TUERCA GIGANTE ROJA" # 3 palabras
        l1, l2 = self.service.partir_en_dos_lineas(texto)
        
        # La primera mitad lleva menos en la división entera de Python (3//2 = 1)
        # Según tu código: palabras[:mitad] -> palabras[:1]
        self.assertEqual(l1, "TUERCA") 
        self.assertEqual(l2, "GIGANTE .")

    def test_partir_una_sola_palabra(self):
        """Si hay una sola palabra, la segunda línea debe estar vacía."""
        texto = "TORNILLO"
        l1, l2 = self.service.partir_en_dos_lineas(texto)
        self.assertEqual(l1, "TORNILLO")
        self.assertEqual(l2, "")

    # ----------------------------------------------------------------
    # 2. TEST DE GENERACIÓN DE RUTAS
    # ----------------------------------------------------------------

    def test_resolver_ruta_pdf_crea_path_correcto(self):
        """Verifica que se construya la ruta completa del archivo."""
        # Creamos un objeto simulado (Mock) que imita una Etiqueta
        etiqueta_mock = MagicMock()
        etiqueta_mock.carpeta = "TORNILLOS/ALTA_RESISTENCIA"
        etiqueta_mock.articulo = "HEXAGONAL"
        etiqueta_mock.medida = "1/4"

        ruta = self.service._resolver_ruta_pdf(etiqueta_mock)
        
        # Verificamos normalización de path (slashes vs backslashes)
        ruta_esperada_final = os.path.join(
            "test_output", 
            "TORNILLOS/ALTA_RESISTENCIA", 
            "HEXAGONAL_1_4.pdf" # El nombre pasa por _safe_filename
        )
        
        # Comparamos paths absolutos para evitar líos de Windows/Linux
        self.assertEqual(os.path.abspath(ruta), os.path.abspath(ruta_esperada_final))

    # ----------------------------------------------------------------
    # 3. TEST DE INTERACCIÓN CON EL SISTEMA (Mocks)
    # ----------------------------------------------------------------

    @patch("etiqueta_pdf_service.ImageReader")
    @patch("etiqueta_pdf_service.canvas.Canvas")
    def test_crear_pdf_no_falla(self, mock_canvas, mock_image_reader):
        """Simula la creación de un PDF sin escribir en disco."""
        
        # Configurar mocks
        mock_image_reader.return_value.getSize.return_value = (100, 100) # Simular tamaño logo
        
        etiqueta_mock = MagicMock()
        etiqueta_mock.articulo = "TEST ART"
        etiqueta_mock.medida = "10MM"
        etiqueta_mock.cantidad = 50
        etiqueta_mock.carpeta = "TEST"
        etiqueta_mock.tipo = "vertical"   # 👈 ESTO FALTABA

        ruta_generada = self.service.crear_pdf_etiqueta(etiqueta_mock)

        # Verificamos que se llamó a guardar el PDF
        mock_canvas.return_value.save.assert_called_once()
        print(f"\n[Test] PDF simulado generado en: {ruta_generada}")

    @patch('etiqueta_pdf_service.subprocess.run')
    @patch('etiqueta_pdf_service.EtiquetaManager') # Mockeamos la DB
    def test_imprimir_etiqueta_llama_sumatra(self, mock_manager_cls, mock_subprocess):
        """Verifica que se llame a SumatraPDF con los argumentos correctos."""
        
        # 1. Preparamos la respuesta de la "Base de datos" falsa
        mock_db_instance = mock_manager_cls.return_value
        etiqueta_mock = MagicMock()
        etiqueta_mock.articulo = "Buje"
        etiqueta_mock.medida = "10"
        etiqueta_mock.carpeta = "Bujes"
        
        mock_db_instance.obtener_por_id.return_value = etiqueta_mock
        
        # 2. Forzamos que os.path.exists diga "True" para no intentar crear el PDF
        with patch('os.path.exists', return_value=True):
            self.service.imprimir_etiqueta(etiqueta_id=1, cantidad_hojas=2)

        # 3. Verificamos la llamada a subprocess (lo más crítico)
        args_llamada, _ = mock_subprocess.call_args
        comando_ejecutado = args_llamada[0]

        self.assertEqual(comando_ejecutado[0], "SumatraPDF.exe")
        self.assertIn("-print-to-default", comando_ejecutado)
        self.assertIn("2x", comando_ejecutado) # Verificamos cantidad
        
        print("\n[Test] Comando enviado a subprocess:", comando_ejecutado)

if __name__ == '__main__':
    unittest.main()