import tkinter as tk
from tkinter import ttk, messagebox
from db_api import EtiquetaManager
from etiqueta_pdf_service import EtiquetaPDFService

import fitz  # PyMuPDF
from PIL import Image, ImageTk

class VisualizadorPDF:
    """Ventana independiente para previsualizar PDFs con scroll total y centrada"""
    def __init__(self, parent, ruta_pdf):
        self.top = tk.Toplevel(parent)
        self.top.title("Previsualización de Etiqueta")
        
        # --- 1. CONFIGURACIÓN DE TAMAÑO Y CENTRADO ---
        ancho_ventana = 800
        alto_ventana = self.top.winfo_screenheight() - 100 # Casi el alto total de pantalla
        
        # Obtener dimensiones de la pantalla para centrar
        screen_width = self.top.winfo_screenwidth()
        screen_height = self.top.winfo_screenheight()
        
        pos_x = (screen_width // 2) - (ancho_ventana // 2)
        pos_y = 0 # Aparece arriba centrado
        
        self.top.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")
        self.top.configure(bg="#34495e")

        # --- 2. CONTENEDOR CON SCROLLS (VERTICAL Y HORIZONTAL) ---
        # Frame contenedor para organizar canvas y barras
        container = tk.Frame(self.top, bg="#34495e")
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, bg="grey", highlightthickness=0)
        
        scroll_y = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scroll_x = tk.Scrollbar(self.top, orient="horizontal", command=self.canvas.xview) # En la base de la ventana
        
        self.canvas.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        # Empaquetado de componentes
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        try:
            # Abrir el PDF
            doc = fitz.open(ruta_pdf)
            page = doc.load_page(0)
            
            # Aumentamos el zoom a 2.5 para que se vea más grande y nítido
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5)) 
            
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.photo = ImageTk.PhotoImage(img)
            
            # Evitar Garbage Collection
            self.canvas.image = self.photo 
            
            # Dibujar la imagen en el centro horizontal del scrollregion
            # Usamos pix.width/2 para que el punto 'n' (norte/arriba) esté centrado
            self.canvas.create_image(pix.width / 2, 20, image=self.photo, anchor="n")
            
            # Configurar el área de scroll exactamente al tamaño del contenido generado
            self.canvas.config(scrollregion=(0, 0, pix.width, pix.height + 100))
            
            doc.close()
            self.top.update_idletasks()

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo renderizar el PDF: {e}")
            self.top.destroy()

class VentanaNueva:
    """Ventana emergente para crear una nueva etiqueta y su PDF"""
    def __init__(self, parent, callback_actualizar):
        self.top = tk.Toplevel(parent)
        self.top.title("Nueva Etiqueta")
        self.top.geometry("350x380")
        self.top.configure(bg="#f2f2f2")
        self.top.grab_set()

        self.callback_actualizar = callback_actualizar
        # Inicializamos el servicio de PDF
        self.pdf_service = EtiquetaPDFService()

        main_frame = tk.Frame(self.top, bg="#f2f2f2", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Campos del formulario
        self._crear_campo(main_frame, "Carpeta / Tipo:", "carpeta", "")
        self._crear_campo(main_frame, "Artículo:", "articulo", "")
        self._crear_campo(main_frame, "Medida:", "medida", "")
        self._crear_campo(main_frame, "Cantidad:", "cantidad", "0")

        btns_frame = tk.Frame(main_frame, bg="#f2f2f2")
        btns_frame.pack(fill="x", pady=(20, 0))

        tk.Button(btns_frame, text="CREAR Y GENERAR PDF", bg="#27ae60", fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", padx=15, 
                  command=self.guardar).pack(side="left")
        
        tk.Button(btns_frame, text="CANCELAR", bg="#7f8c8d", fg="white", 
                  font=("Segoe UI", 9, "bold"), relief="flat", padx=15, 
                  command=self.top.destroy).pack(side="right")

    def _crear_campo(self, parent, label_text, attr_name, valor_inicial):
        tk.Label(parent, text=label_text, bg="#f2f2f2", font=("Segoe UI", 9)).pack(anchor="w")
        ent = tk.Entry(parent, font=("Segoe UI", 10))
        ent.insert(0, str(valor_inicial))
        ent.pack(fill="x", pady=(0, 10))
        setattr(self, f"entry_{attr_name}", ent)

    def guardar(self):
        articulo = self.entry_articulo.get().strip()
        carpeta = self.entry_carpeta.get().strip()
        medida = self.entry_medida.get().strip()
        cantidad = self.entry_cantidad.get().strip()
        
        if not articulo or not carpeta:
            messagebox.showwarning("Error", "Los campos Carpeta y Artículo son obligatorios")
            return

        datos = {
            "carpeta": carpeta,
            "articulo": articulo,
            "medida": medida,
            "cantidad": cantidad
        }

        manager = EtiquetaManager()
        try:
            # 1. Guardar en Base de Datos
            nueva_etiqueta = manager.crear(**datos) # Asumimos que manager.crear devuelve el objeto creado
            
            if nueva_etiqueta:
                # 2. Generar el PDF usando el servicio
                # El servicio espera un objeto que tenga .articulo, .medida, etc.
                ruta_pdf = self.pdf_service.crear_pdf_etiqueta(nueva_etiqueta)
                
                # 3. Mensaje de confirmación final
                messagebox.showinfo("Éxito", 
                    f"Etiqueta guardada en DB.\n\nPDF generado en:\n{ruta_pdf}")
                
                self.callback_actualizar() 
                self.top.destroy()
            else:
                messagebox.showerror("Error", "No se pudo insertar en la base de datos.")

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")
        finally:
            manager.cerrar()

class VentanaEditar:
    """Ventana emergente para editar los detalles de una etiqueta"""
    def __init__(self, parent, etiqueta_obj, callback_actualizar):
        self.top = tk.Toplevel(parent)
        self.top.title("Editar Etiqueta")
        self.top.geometry("350x300")
        self.top.configure(bg="#f2f2f2")
        self.top.grab_set()

        self.etiqueta = etiqueta_obj
        self.callback_actualizar = callback_actualizar

        main_frame = tk.Frame(self.top, bg="#f2f2f2", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        self._crear_campo(main_frame, "Artículo:", "articulo", etiqueta_obj.articulo)
        self._crear_campo(main_frame, "Medida:", "medida", etiqueta_obj.medida)
        # El campo cantidad en la DB suele ser numérico, pero permitimos texto en la UI
        self._crear_campo(main_frame, "Cantidad (Base de datos):", "cantidad", etiqueta_obj.cantidad)

        btns_frame = tk.Frame(main_frame, bg="#f2f2f2")
        btns_frame.pack(fill="x", pady=(20, 0))

        tk.Button(btns_frame, text="GUARDAR", bg="#27ae60", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=15, command=self.guardar).pack(side="left")
        
        tk.Button(btns_frame, text="CANCELAR", bg="#7f8c8d", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", padx=15, command=self.top.destroy).pack(side="right")

    def _crear_campo(self, parent, label_text, attr_name, valor_inicial):
        tk.Label(parent, text=label_text, bg="#f2f2f2", font=("Segoe UI", 9)).pack(anchor="w")
        ent = tk.Entry(parent, font=("Segoe UI", 10))
        ent.insert(0, str(valor_inicial))
        ent.pack(fill="x", pady=(0, 10))
        setattr(self, f"entry_{attr_name}", ent)

    def guardar(self):
        val_cantidad = self.entry_cantidad.get().strip()
        # Intentamos convertir a int para la DB, si no, lo dejamos en 0 o manejamos el error
        try:
            cant_db = val_cantidad
        except:
            cant_db = 0

        nuevos_datos = {
            "articulo": self.entry_articulo.get().strip(),
            "medida": self.entry_medida.get().strip(),
            "cantidad": cant_db
        }

        manager = EtiquetaManager()
        try:
            exito = manager.modificar(self.etiqueta.id, **nuevos_datos)
            if exito:
                self.etiqueta.articulo = nuevos_datos["articulo"]
                self.etiqueta.medida = nuevos_datos["medida"]
                self.etiqueta.cantidad = nuevos_datos["cantidad"]
                self.callback_actualizar() 
                self.top.destroy()
        finally:
            manager.cerrar()

class InterfazEstricta:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Etiquetas")
        self.root.geometry("800x600") 
        self.root.configure(bg="#f2f2f2")

        self.pdf_service = EtiquetaPDFService()
        # Eliminamos vcmd porque ya no validamos solo números
        
        self.filas = [] 
        self.etiquetas_cache = [] 
        self.search_timer = None  
        
        self.ANCHO_SELECCION = 60
        self.ANCHO_CANTIDAD = 120
        self.ALTO_FILA = 32   

        self.crear_interfaz()
        self.cargar_datos_iniciales()

    def crear_interfaz(self):
        print("creando interfaz")#borrar
        top = tk.Frame(self.root, bg="#f2f2f2")
        top.pack(fill="x", padx=16, pady=(12, 8))

        self._btn(top, "IMPRIMIR", "#27ae60", "#ffffff", self.imprimir_etiquetas_ingresadas).pack(side="left", padx=(0, 10))
        self._btn(top, "LIMPIAR TODO", "#7f8c8d", "#ffffff", self.limpiar_todas_las_cantidades).pack(side="left")
        self._btn(top, "NUEVA ETIQUETA", "#2980b9", "#ffffff", 
          command=lambda: VentanaNueva(self.root, self.cargar_datos_iniciales)).pack(side="right")

        self.entry_search = tk.Entry(self.root, font=("Segoe UI", 11), relief="flat", bg="white", highlightthickness=1, highlightbackground="#cccccc")
        self.entry_search.pack(fill="x", padx=16, pady=(0, 12), ipady=4)
        self.entry_search.insert(0, "Buscar etiqueta...")
        
        self.entry_search.bind("<FocusIn>", lambda e: self._on_search_focus(True))
        self.entry_search.bind("<FocusOut>", lambda e: self._on_search_focus(False))
        self.entry_search.bind("<KeyRelease>", self._on_search_typing)

        header = tk.Frame(self.root, bg="#34495e", height=42)
        header.pack(fill="x", padx=16)
        header.pack_propagate(False)

        self._header_cell(header, "Editar", width=self.ANCHO_SELECCION)
        self._header_cell(header, "Etiqueta", expand=True)
        self._header_cell(header, "Cantidad", width=self.ANCHO_CANTIDAD)

        container = tk.Frame(self.root, bg="#f2f2f2")
        container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.canvas = tk.Canvas(container, bg="#f2f2f2", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.scrollable = tk.Frame(self.canvas, bg="#f2f2f2")
        self.scrollable.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width))

    def _btn(self, parent, text, color_bg, color_fg, command=None):
        btn = tk.Button(parent, text=text, command=command, font=("Segoe UI", 9, "bold"),
                        bg=color_bg, fg=color_fg, relief="raised", borderwidth=1,
                        padx=20, pady=5, cursor="hand2")
        return btn

    def _header_cell(self, parent, text, width=None, expand=False):
        cell = tk.Frame(parent, bg="#34495e", width=width, height=44)
        cell.pack(side="left", fill="both", expand=expand)
        cell.pack_propagate(False)
        tk.Label(cell, text=text.upper(), font=("Segoe UI", 8, "bold"), bg="#34495e", fg="white", anchor="center").pack(fill="both", expand=True)

    def _on_search_typing(self, event):
        if self.search_timer:
            self.root.after_cancel(self.search_timer)
        self.search_timer = self.root.after(500, self._ejecutar_busqueda)
        
    def _ejecutar_busqueda(self):
        query = self.entry_search.get().lower().strip()
        if query == "buscar etiqueta..." or not query:
            self.renderizar_tabla(self.etiquetas_cache)
            return

        terminos = query.split()
        resultados = []
        for etiqueta in self.etiquetas_cache:
            contenido_fila = f"{etiqueta.carpeta} {etiqueta.medida} {etiqueta.articulo}".lower().replace("-", "/")
            if all(t in contenido_fila for t in terminos):
                resultados.append(etiqueta)
        self.renderizar_tabla(resultados)

    def cargar_datos_iniciales(self):
        print("cargando datos iniciales")#borrar
        manager = EtiquetaManager()
        try:
            raw_etiquetas = manager.listar_todas()
            self.etiquetas_cache = sorted(raw_etiquetas, key=lambda e: f"{e.articulo} {e.medida}".lower())
            for e in self.etiquetas_cache:
                e.cantidad_temp = "" 
            self.renderizar_tabla(self.etiquetas_cache)
        finally:
            manager.cerrar()

    def renderizar_tabla(self, lista_etiquetas):
        print("renderizando tabla")#borrar
        self.limpiar_tabla()
        for etiqueta in lista_etiquetas:
            # Mostramos medida con barras
            medida_display = etiqueta.medida.replace('-', '/') if etiqueta.medida else ""
            texto = f"{etiqueta.carpeta.split('/')[0]} | {medida_display} | {etiqueta.articulo} | {etiqueta.cantidad}"
            self.agregar_fila(etiqueta, texto)
        print("se renderizo la la tabla")#borrar

    def agregar_fila(self, etiqueta_obj, texto):
        row = tk.Frame(self.scrollable, bg="white", height=self.ALTO_FILA)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # --- BOTÓN EDITAR ---
        btn_edit = tk.Button(row, text="✎", font=("Segoe UI", 11), bg="white", fg="#2980b9",
                             relief="flat", cursor="hand2", borderwidth=0, width=4,
                             command=lambda: VentanaEditar(self.root, etiqueta_obj, self._ejecutar_busqueda))
        btn_edit.pack(side="left")

        # --- NUEVO: BOTÓN VER PDF (OJO) ---
        def ver_pdf():
            service = EtiquetaPDFService()
            # Obtenemos la ruta del PDF. Si no existe, lo crea.
            ruta = service.crear_pdf_etiqueta(etiqueta_obj) 
            VisualizadorPDF(self.root, ruta)

        btn_view = tk.Button(row, text="👁", font=("Segoe UI", 11), bg="white", fg="#27ae60",
                             relief="flat", cursor="hand2", borderwidth=0, width=4,
                             command=ver_pdf)
        btn_view.pack(side="left")

        # --- TEXTO ETIQUETA ---
        tk.Label(row, text=texto, anchor="w", font=("Segoe UI", 10), bg="white", fg="#333", padx=10).pack(side="left", fill="both", expand=True)

        # --- CANTIDAD ---
        qty_container = tk.Frame(row, bg="#d0d0d0", padx=1, pady=1)
        qty_container.pack(side="right", padx=18)

        qty_var = tk.StringVar(value=etiqueta_obj.cantidad_temp)
        qty_var.trace_add("write", lambda *a: setattr(etiqueta_obj, 'cantidad_temp', qty_var.get()))

        cell_qty = tk.Entry(qty_container, width=10, justify="center", textvariable=qty_var,
                            font=("Segoe UI", 10, "bold"), relief="flat", bg="white", fg="#222")
        cell_qty.pack(ipady=4)
        
        self.filas.append({"obj": etiqueta_obj, "var": qty_var})

    def limpiar_todas_las_cantidades(self):
        for etiqueta in self.etiquetas_cache:
            etiqueta.cantidad_temp = ""
        self._ejecutar_busqueda()

    def imprimir_etiquetas_ingresadas(self):
        lista_para_imprimir = []
        for etiqueta in self.etiquetas_cache:
            valor = etiqueta.cantidad_temp.strip()
            if valor: # Si hay algo escrito (sea número o "2 kg")
                # NOTA: Asegúrate que tu pdf_service soporte strings en la cantidad o extrae el número
                lista_para_imprimir.append((etiqueta.id, valor))
        
        if not lista_para_imprimir: return
        
        self.pdf_service.imprimir_lista_etiquetas(lista_para_imprimir)
        self.limpiar_todas_las_cantidades()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def limpiar_tabla(self):
        for widget in self.scrollable.winfo_children():
            widget.destroy()
        self.filas.clear()

    def _on_search_focus(self, has_focus):
        texto = self.entry_search.get()
        if has_focus and texto == "Buscar etiqueta...":
            self.entry_search.delete(0, tk.END)
        elif not has_focus and not texto:
            self.entry_search.insert(0, "Buscar etiqueta...")

if __name__ == "__main__":
    print("programa en ejecucion...")#borrar
    root = tk.Tk()
    InterfazEstricta(root)
    root.mainloop()