import os
import subprocess
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
import threading
from tools import resource_path

from db_api import EtiquetaManager

MM = 2.83465
PAGE_WIDTH, PAGE_HEIGHT = A4

LABEL_WIDTH = 64 * MM
LABEL_HEIGHT = 34 * MM

MARGIN_TOP = 12 * MM
MARGIN_LEFT = 6.5 * MM
COLUMN_GAP = 4 * MM

COLUMNS = 3
ROWS = 8
LOGO_HEIGHT = 6 * MM


class EtiquetaPDFService:
    def __init__(self, base_output="etiquetas_pdf", logo_path="LOGO_LUQUE.png"):
        self.base_output = base_output
        self.logo_path = resource_path(logo_path)
        #self.logo_path = logo_path
        os.makedirs(self.base_output, exist_ok=True)

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    def _safe_filename(self, text):
        return (
            text.replace("/", "_")
                .replace("\\", "_")
                .replace(" ", "_")
                .replace(".", "-")
        )

    def _resolver_ruta_pdf(self, etiqueta):
        carpeta = etiqueta.carpeta or "SIN_CARPETA"
        ruta = os.path.join(self.base_output, carpeta)
        os.makedirs(ruta, exist_ok=True)

        nombre = f"{etiqueta.articulo}_{etiqueta.medida}"
        nombre = self._safe_filename(nombre) + ".pdf"

        return os.path.join(ruta, nombre)

    # ------------------------------------------------------------------
    # 1. CREAR PDF DE UNA ETIQUETA
    # ------------------------------------------------------------------

    def crear_pdf_etiqueta(self, etiqueta):
        ruta_pdf = self._resolver_ruta_pdf(etiqueta)
        c = canvas.Canvas(ruta_pdf, pagesize=A4)

        logo = ImageReader(self.logo_path)
        logo_w, logo_h = logo.getSize()
        logo_scale = LOGO_HEIGHT / logo_h
        logo_width_scaled = logo_w * logo_scale

        y_start = PAGE_HEIGHT - MARGIN_TOP - LABEL_HEIGHT
        alto_texto = LABEL_HEIGHT - 4 * MM   # margen de seguridad

        for row in range(ROWS):
            y = y_start - row * LABEL_HEIGHT

            for col in range(COLUMNS):
                x = MARGIN_LEFT + col * (LABEL_WIDTH + COLUMN_GAP)

                # LOGO
                c.drawImage(
                    logo,
                    x + (LABEL_WIDTH - logo_width_scaled) / 2,
                    y + LABEL_HEIGHT - LOGO_HEIGHT - 1.5 * MM,
                    width=logo_width_scaled,
                    height=LOGO_HEIGHT,
                    mask="auto"
                )

                # MEDIDA
                c.saveState()
                c.translate(x + 8 * MM, y + LABEL_HEIGHT / 2)
                c.rotate(90)
                c.setFont("Helvetica-Bold", 16)
                c.drawCentredString(0, 0, etiqueta.medida)
                c.restoreState()


                # -------- ARTICULO (CON MARGEN SUPERIOR DE 6mm) --------
                fuente = "Helvetica"
                size = 12
                texto = etiqueta.articulo
                
                # 1. Definimos el margen que queremos "cortar" de arriba
                MARGEN_SUPERIOR_LOGO = 6 * MM
                
                # 2. Calculamos la altura real disponible para escribir
                # (Altura total - margen superior - un pequeño margen inferior de seguridad)
                alto_zona_segura = LABEL_HEIGHT - MARGEN_SUPERIOR_LOGO
                
                # 3. Calculamos el NUEVO centro vertical
                # En lugar de ir al centro de la etiqueta, vamos al centro de la zona segura.
                # Visualmente esto "baja" el punto de escritura.
                y_centro_seguro = y + (alto_zona_segura / 2)

                c.saveState()
                # Trasladamos el origen al centro de la zona segura (no al centro de la etiqueta)
                c.translate(x + LABEL_WIDTH / 2, y_centro_seguro)
                c.rotate(90)
                c.setFont(fuente, size)

                # Usamos el alto_zona_segura para calcular si entra el texto
                if self.texto_entra_vertical(texto, fuente, size, alto_zona_segura):
                    # ✔ Entra en una línea
                    # Al haber ajustado el 'translate', ya no necesitamos offsets extraños como -margen_logo
                    # Dibujamos en (0,0) que ahora es el centro del espacio libre
                    c.drawCentredString(0, 0, texto)

                else:
                    # ❌ No entra → partir en dos líneas
                    l1, l2 = self.partir_en_dos_lineas(texto)
                    interlineado = size + 2
                    
                    # Dibujamos centrado en el nuevo punto de origen
                    c.drawCentredString(0, interlineado / 2, l1)
                    c.drawCentredString(0, -interlineado / 2, l2)

                c.restoreState()
                # ----------------------------------------


                # CANTIDAD
                c.saveState()
                c.translate(x + LABEL_WIDTH - 8 * MM, y + LABEL_HEIGHT / 2)
                c.rotate(90)
                c.setFont("Helvetica-Bold", 26)
                c.drawCentredString(0, 0, str(etiqueta.cantidad))
                c.restoreState()

        c.save()
        return ruta_pdf

    
    def texto_entra_vertical(self, texto, fuente, tamaño, alto_disponible):
        margen = 7 * MM
        return stringWidth(texto, fuente, tamaño) <= (alto_disponible - margen)


    def partir_en_dos_lineas(self, texto):
        """
        Parte el texto en dos líneas lo más balanceadas posible
        """
        palabras = texto.split()
        if len(palabras) <= 1:
            return texto, ""

        mitad = len(palabras) // 2
        linea1 = " ".join(palabras[:mitad])
        linea2 = " ".join(palabras[mitad:])
        return linea1, linea2

    # ------------------------------------------------------------------
    # 2. CREAR TODAS LAS ETIQUETAS DE LA DB
    # ------------------------------------------------------------------

    def crear_todas_las_etiquetas(self):
        manager = EtiquetaManager()
        etiquetas = manager.listar_todas()

        rutas = []
        for etiqueta in etiquetas:
            ruta = self.crear_pdf_etiqueta(etiqueta)
            rutas.append(ruta)

        manager.cerrar()
        return rutas

    # ------------------------------------------------------------------
    # 3. IMPRIMIR UNA ETIQUETA CON SUMATRA
    # ------------------------------------------------------------------

    def imprimir_etiqueta(
        self,
        etiqueta_id,
        cantidad_hojas=1,
        sumatra_path="SumatraPDF.exe"
    ):
        manager = EtiquetaManager()
        etiqueta = manager.obtener_por_id(etiqueta_id)
        manager.cerrar()

        if not etiqueta:
            raise ValueError("Etiqueta no encontrada")

        pdf_path = self._resolver_ruta_pdf(etiqueta)

        if not os.path.exists(pdf_path):
            pdf_path = self.crear_pdf_etiqueta(etiqueta)

        # Seguridad mínima
        cantidad_hojas = max(1, int(cantidad_hojas))

        subprocess.run([
            sumatra_path,
            "-print-to-default",
            "-print-settings",
            f"{cantidad_hojas}x",
            "-silent",
            pdf_path
        ], check=True)


    def imprimir_lista_etiquetas(
        self,
        etiquetas,
        sumatra_path="SumatraPDF.exe"
    ):
        """
        etiquetas: lista de tuplas (etiqueta_id, cantidad_hojas)
        Se imprime en un hilo separado para no congelar la UI.
        """
        if not etiquetas:
            return

        def _worker():
            for etiqueta_id, cantidad_hojas in etiquetas:
                try:
                    self.imprimir_etiqueta(
                        etiqueta_id=etiqueta_id,
                        cantidad_hojas=cantidad_hojas,
                        sumatra_path=sumatra_path
                    )
                except Exception as e:
                    print(
                        f"Error imprimiendo etiqueta {etiqueta_id}: {e}"
                    )

        threading.Thread(
            target=_worker,
            daemon=True   # mata el hilo al cerrar la app
        ).start()
if __name__ == "__main__":
    pdf_service = EtiquetaPDFService()

    # Crear todos los PDFs
    pdf_service.crear_todas_las_etiquetas()
