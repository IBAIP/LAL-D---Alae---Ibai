import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from tkcalendar import Calendar

# La base de datos se guarda junto al script, no donde se ejecute el programa
DB_PATH = Path(__file__).with_name('mis_recordatorios.db')
PLACEHOLDER = 'Escribe un recordatorio...'
INTERVALO_COMPROBACION_MS = 15_000  # cada cuánto se buscan recordatorios vencidos

FORMATO_FECHA = '%Y-%m-%d'
FORMATO_HORA = '%H:%M'

# ---- Identidad de la causa ----
CAUSA_NOMBRE = 'ALDE'
CAUSA_LEMA = 'Organizándonos por la causa'
CAUSA_COLOR = '#2f6f5e'


def mezclar(color, con, cantidad):
    """Mezcla dos colores hex. cantidad=0.85 con blanco da un tinte muy suave del color."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(con[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * cantidad):02x}' for x, y in zip(a, b))


def normalizar_hora(texto):
    """Devuelve la hora como 'HH:MM' o None si no es válida."""
    try:
        return datetime.strptime(texto.strip(), FORMATO_HORA).strftime(FORMATO_HORA)
    except ValueError:
        return None


class BaseDatos:
    """Toda la lógica SQLite en un solo sitio, separada de la interfaz."""

    def __init__(self, ruta):
        self.conn = sqlite3.connect(ruta)
        self._preparar_tabla()

    def _preparar_tabla(self):
        with self.conn:
            # Tabla original de recordatorios
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS recordatorios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    tarea TEXT NOT NULL,
                    notificado INTEGER NOT NULL DEFAULT 0
                )
            ''')
            # Nueva tabla para alimentación
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS alimentacion (
                    fecha TEXT PRIMARY KEY,
                    desayuno TEXT,
                    comida TEXT,
                    merienda TEXT,
                    cena TEXT
                )
            ''')
            
            # Migración recordatorios (por si venimos de versiones viejas)
            columnas = {f[1] for f in self.conn.execute('PRAGMA table_info(recordatorios)')}
            if 'notificado' not in columnas:
                self.conn.execute('ALTER TABLE recordatorios ADD COLUMN notificado INTEGER NOT NULL DEFAULT 0')
                ahora = datetime.now().strftime(f'{FORMATO_FECHA} {FORMATO_HORA}')
                self.conn.execute("UPDATE recordatorios SET notificado = 1 WHERE fecha || ' ' || hora <= ?", (ahora,))

    # --- Métodos Recordatorios ---
    def añadir_recordatorio(self, fecha, hora, tarea, notificado=False):
        with self.conn:
            self.conn.execute(
                'INSERT INTO recordatorios (fecha, hora, tarea, notificado) VALUES (?, ?, ?, ?)',
                (fecha, hora, tarea, int(notificado)),
            )

    def listar_recordatorios(self, fecha):
        return self.conn.execute(
            'SELECT id, hora, tarea FROM recordatorios WHERE fecha = ? ORDER BY hora, id',
            (fecha,),
        ).fetchall()

    def eliminar_recordatorio(self, id_recordatorio):
        with self.conn:
            self.conn.execute('DELETE FROM recordatorios WHERE id = ?', (id_recordatorio,))

    def fechas_con_recordatorios(self):
        filas = self.conn.execute('SELECT DISTINCT fecha FROM recordatorios').fetchall()
        return [f[0] for f in filas]

    def pendientes(self, ahora):
        return self.conn.execute(
            "SELECT id, fecha, hora, tarea FROM recordatorios "
            "WHERE notificado = 0 AND fecha || ' ' || hora <= ? ORDER BY fecha, hora",
            (ahora,),
        ).fetchall()

    def marcar_notificado(self, id_recordatorio):
        with self.conn:
            self.conn.execute('UPDATE recordatorios SET notificado = 1 WHERE id = ?', (id_recordatorio,))

    # --- Métodos Alimentación ---
    def guardar_comidas(self, fecha, desayuno, comida, merienda, cena):
        with self.conn:
            # REPLACE INTO inserta si no existe, o reemplaza toda la fila si ya existe la clave primaria (fecha)
            self.conn.execute(
                'REPLACE INTO alimentacion (fecha, desayuno, comida, merienda, cena) VALUES (?, ?, ?, ?, ?)',
                (fecha, desayuno, comida, merienda, cena)
            )

    def obtener_comidas(self, fecha):
        fila = self.conn.execute(
            'SELECT desayuno, comida, merienda, cena FROM alimentacion WHERE fecha = ?', 
            (fecha,)
        ).fetchone()
        return fila if fila else ("", "", "", "")

    def cerrar(self):
        self.conn.close()


class AplicacionRecordatorios:
    # Paleta minimalista
    BG = '#fafaf8'
    CARD = '#ffffff'
    LINE = '#e5e7eb'
    TEXT = '#1f2933'
    MUTED = '#8a94a0'
    DANGER = '#c0392b'
    ON_ACCENT = '#ffffff'
    ACCENT = CAUSA_COLOR
    ACCENT_HOVER = mezclar(CAUSA_COLOR, '#000000', 0.15)
    TINT = mezclar(CAUSA_COLOR, '#ffffff', 0.85)

    def __init__(self, root):
        self.root = root
        self.root.title(f'{CAUSA_NOMBRE} · Organización')
        self.root.geometry('460x800') # Un poco más alta para que quepa bien el formulario
        self.root.config(bg=self.BG)

        self.db = BaseDatos(DB_PATH)
        self.ids_visibles = []
        self.pestaña_activa = "recordatorios"

        self.configurar_interfaz()
        self.al_seleccionar_fecha()
        self.marcar_dias_con_recordatorios()

        self.root.protocol('WM_DELETE_WINDOW', self.cerrar)
        self.comprobar_recordatorios()

    def configurar_interfaz(self):
        main_frame = tk.Frame(self.root, bg=self.BG)
        main_frame.pack(fill='both', expand=True, padx=24, pady=24)

        # --- Cabecera ---
        cabecera = tk.Frame(main_frame, bg=self.BG)
        cabecera.pack(fill='x')

        tk.Label(
            cabecera, text=CAUSA_NOMBRE, bg=self.ACCENT, fg=self.ON_ACCENT,
            font=('Segoe UI', 11, 'bold'), padx=10, pady=6,
        ).pack(side='left')

        textos = tk.Frame(cabecera, bg=self.BG)
        textos.pack(side='left', padx=(12, 0))
        tk.Label(textos, text='Gestión Diaria', bg=self.BG, fg=self.TEXT, font=('Segoe UI', 15, 'bold')).pack(anchor='w')
        tk.Label(textos, text=CAUSA_LEMA, bg=self.BG, fg=self.MUTED, font=('Segoe UI', 9)).pack(anchor='w')

        tk.Frame(main_frame, bg=self.ACCENT, height=2).pack(fill='x', pady=16)

        # --- Calendario ---
        self.calendario = Calendar(
            main_frame, selectmode='day', date_pattern='yyyy-mm-dd',
            background=self.ACCENT, foreground=self.ON_ACCENT,
            selectbackground=self.ACCENT, selectforeground=self.ON_ACCENT,
            normalbackground=self.CARD, normalforeground=self.TEXT,
            weekendbackground=self.CARD, weekendforeground=self.MUTED,
            othermonthbackground=self.BG, othermonthforeground='#c4cad1',
            othermonthwebackground=self.BG, othermonthweforeground='#c4cad1',
            headersbackground=self.BG, headersforeground=self.MUTED,
            bordercolor=self.LINE, font=('Segoe UI', 10),
        )
        self.calendario.tag_config('recordatorio', background=self.TINT, foreground=self.ACCENT)
        self.calendario.pack(fill='x')
        self.calendario.bind('<<CalendarSelected>>', lambda e: self.al_seleccionar_fecha())

        # --- Selector de Pestañas ---
        tabs_frame = tk.Frame(main_frame, bg=self.BG)
        tabs_frame.pack(fill='x', pady=(16, 10))

        estilo_tab = dict(font=('Segoe UI', 10, 'bold'), bd=0, relief='flat', cursor='hand2', width=16)

        self.btn_tab_rec = tk.Button(tabs_frame, text="🔔 Recordatorios", command=self.mostrar_recordatorios, **estilo_tab)
        self.btn_tab_rec.pack(side='left', fill='x', expand=True, padx=(0, 5), ipady=4)
        
        self.btn_tab_ali = tk.Button(tabs_frame, text="🍎 Alimentación", command=self.mostrar_alimentacion, **estilo_tab)
        self.btn_tab_ali.pack(side='right', fill='x', expand=True, padx=(5, 0), ipady=4)

        # Contenedor principal donde se alternan las vistas
        self.contenedor_vistas = tk.Frame(main_frame, bg=self.BG)
        self.contenedor_vistas.pack(fill='both', expand=True)

        self.construir_vista_recordatorios()
        self.construir_vista_alimentacion()
        
        # Iniciar en recordatorios
        self.mostrar_recordatorios()

    def construir_vista_recordatorios(self):
        self.frame_recordatorios = tk.Frame(self.contenedor_vistas, bg=self.BG)
        
        marco_lista = tk.Frame(self.frame_recordatorios, bg=self.LINE)
        marco_lista.pack(fill='both', expand=True, pady=(0, 10))
        
        self.lista_tareas = tk.Listbox(
            marco_lista, bg=self.CARD, fg=self.TEXT,
            selectbackground=self.TINT, selectforeground=self.TEXT,
            font=('Segoe UI', 11), bd=0, highlightthickness=0, relief='flat', activestyle='none',
        )
        self.lista_tareas.pack(fill='both', expand=True, padx=1, pady=1)
        self.lista_tareas.bind('<Delete>', lambda e: self.eliminar_tarea())

        form_frame = tk.Frame(self.frame_recordatorios, bg=self.BG)
        form_frame.pack(fill='x', pady=(5, 8))

        estilo_entrada = dict(bg=self.CARD, insertbackground=self.TEXT, font=('Segoe UI', 11),
                              bd=0, relief='flat', highlightthickness=1,
                              highlightbackground=self.LINE, highlightcolor=self.ACCENT)

        self.input_hora = tk.Entry(form_frame, width=6, fg=self.TEXT, **estilo_entrada)
        self.input_hora.pack(side='left', ipady=7, padx=(0, 8))
        self.input_hora.insert(0, '10:00')
        self.input_hora.bind('<Return>', lambda e: self.añadir_tarea())

        self.input_tarea = tk.Entry(form_frame, fg=self.MUTED, **estilo_entrada)
        self.input_tarea.pack(side='left', fill='x', expand=True, ipady=7, padx=(0, 8))
        self.input_tarea.insert(0, PLACEHOLDER)
        self.input_tarea.bind('<FocusIn>', self._limpiar_placeholder)
        self.input_tarea.bind('<FocusOut>', self._restaurar_placeholder)
        self.input_tarea.bind('<Return>', lambda e: self.añadir_tarea())

        btn_añadir = tk.Button(
            form_frame, text='Añadir', bg=self.ACCENT, fg=self.ON_ACCENT,
            font=('Segoe UI', 10, 'bold'), bd=0, relief='flat',
            cursor='hand2', command=self.añadir_tarea,
        )
        btn_añadir.pack(side='right', ipadx=10, ipady=4)

        btn_eliminar = tk.Button(
            self.frame_recordatorios, text='Eliminar seleccionada', bg=self.BG, fg=self.MUTED,
            activebackground=self.BG, activeforeground=self.DANGER,
            font=('Segoe UI', 9), bd=0, relief='flat', cursor='hand2', command=self.eliminar_tarea,
        )
        btn_eliminar.pack(anchor='e')

    def construir_vista_alimentacion(self):
        self.frame_alimentacion = tk.Frame(self.contenedor_vistas, bg=self.BG)
        
        estilo_entrada = dict(bg=self.CARD, insertbackground=self.TEXT, font=('Segoe UI', 11),
                              bd=0, relief='flat', highlightthickness=1,
                              highlightbackground=self.LINE, highlightcolor=self.ACCENT)

        self.inputs_comida = {}
        comidas = [("Desayuno", "☕"), ("Comida", "🍲"), ("Merienda", "🥪"), ("Cena", "🥗")]

        for titulo, icono in comidas:
            row = tk.Frame(self.frame_alimentacion, bg=self.BG)
            row.pack(fill='x', pady=4)
            tk.Label(row, text=f"{icono} {titulo}", bg=self.BG, fg=self.TEXT, font=('Segoe UI', 9, 'bold')).pack(anchor='w')
            
            # Usamos Entry para que sea compacto y ocupe menos espacio vertical
            entry = tk.Entry(row, fg=self.TEXT, **estilo_entrada)
            entry.pack(fill='x', ipady=6)
            self.inputs_comida[titulo] = entry

        btn_guardar_comidas = tk.Button(
            self.frame_alimentacion, text='Guardar Registro Diario', bg=self.ACCENT, fg=self.ON_ACCENT,
            font=('Segoe UI', 10, 'bold'), bd=0, relief='flat', cursor='hand2',
            command=self.guardar_alimentacion,
        )
        btn_guardar_comidas.pack(fill='x', pady=(15, 0), ipady=8)

    # ------------------------------------------------------------------ Navegación Pestañas
    def mostrar_recordatorios(self):
        self.pestaña_activa = "recordatorios"
        self.frame_alimentacion.pack_forget()
        self.frame_recordatorios.pack(fill='both', expand=True)
        
        self.btn_tab_rec.config(bg=self.ACCENT, fg=self.ON_ACCENT)
        self.btn_tab_ali.config(bg=self.LINE, fg=self.TEXT)

    def mostrar_alimentacion(self):
        self.pestaña_activa = "alimentacion"
        self.frame_recordatorios.pack_forget()
        self.frame_alimentacion.pack(fill='both', expand=True)
        
        self.btn_tab_ali.config(bg=self.ACCENT, fg=self.ON_ACCENT)
        self.btn_tab_rec.config(bg=self.LINE, fg=self.TEXT)

    # ------------------------------------------------------------------ Acciones Globales
    def al_seleccionar_fecha(self):
        """Actualiza ambas vistas (Recordatorios y Alimentación) al cambiar de día en el calendario."""
        fecha = self.calendario.get_date()
        
        # 1. Actualizar lista recordatorios
        self.lista_tareas.delete(0, tk.END)
        self.ids_visibles = []
        registros = self.db.listar_recordatorios(fecha)
        if registros:
            for id_, hora, tarea in registros:
                self.ids_visibles.append(id_)
                self.lista_tareas.insert(tk.END, f'{hora} - {tarea}')
        else:
            self.lista_tareas.insert(tk.END, '  Sin recordatorios para este día.')

        # 2. Actualizar formulario alimentación
        desayuno, comida, merienda, cena = self.db.obtener_comidas(fecha)
        self.inputs_comida["Desayuno"].delete(0, tk.END)
        self.inputs_comida["Desayuno"].insert(0, desayuno)
        
        self.inputs_comida["Comida"].delete(0, tk.END)
        self.inputs_comida["Comida"].insert(0, comida)
        
        self.inputs_comida["Merienda"].delete(0, tk.END)
        self.inputs_comida["Merienda"].insert(0, merienda)
        
        self.inputs_comida["Cena"].delete(0, tk.END)
        self.inputs_comida["Cena"].insert(0, cena)

    def _limpiar_placeholder(self, _event=None):
        if self.input_tarea.get() == PLACEHOLDER:
            self.input_tarea.delete(0, tk.END)
            self.input_tarea.config(fg=self.TEXT)

    def _restaurar_placeholder(self, _event=None):
        if not self.input_tarea.get().strip():
            self.input_tarea.delete(0, tk.END)
            self.input_tarea.insert(0, PLACEHOLDER)
            self.input_tarea.config(fg=self.MUTED)

    # ------------------------------------------------------------------ Acciones Recordatorios
    def añadir_tarea(self):
        fecha = self.calendario.get_date()
        hora = normalizar_hora(self.input_hora.get())
        tarea = self.input_tarea.get().strip()

        if hora is None:
            messagebox.showwarning('Hora no válida', 'Escribe la hora con formato HH:MM (por ejemplo 09:30).')
            return
        if not tarea or tarea == PLACEHOLDER:
            messagebox.showwarning('Aviso', 'Escribe el texto del recordatorio.')
            return

        ya_paso = f'{fecha} {hora}' <= datetime.now().strftime(f'{FORMATO_FECHA} {FORMATO_HORA}')
        if ya_paso and not messagebox.askyesno('Fecha pasada', 'Esa fecha ya pasó.\n¿Guardarlo igualmente?'):
            return

        self.db.añadir_recordatorio(fecha, hora, tarea, notificado=ya_paso)
        
        self.input_hora.delete(0, tk.END)
        self.input_hora.insert(0, hora)
        self.input_tarea.delete(0, tk.END)
        self.al_seleccionar_fecha()
        self.marcar_dias_con_recordatorios()

    def eliminar_tarea(self):
        seleccion = self.lista_tareas.curselection()
        if not seleccion:
            messagebox.showinfo('Aviso', 'Selecciona una tarea de la lista para eliminar.')
            return

        indice = seleccion[0]
        if indice >= len(self.ids_visibles):
            return

        self.db.eliminar_recordatorio(self.ids_visibles[indice])
        self.al_seleccionar_fecha()
        self.marcar_dias_con_recordatorios()

    def marcar_dias_con_recordatorios(self):
        self.calendario.calevent_remove('all')
        for fecha in self.db.fechas_con_recordatorios():
            try:
                dia = datetime.strptime(fecha, FORMATO_FECHA).date()
            except ValueError:
                continue
            self.calendario.calevent_create(dia, 'Recordatorio', 'recordatorio')

    # ------------------------------------------------------------------ Acciones Alimentación
    def guardar_alimentacion(self):
        fecha = self.calendario.get_date()
        d = self.inputs_comida["Desayuno"].get().strip()
        c = self.inputs_comida["Comida"].get().strip()
        m = self.inputs_comida["Merienda"].get().strip()
        ce = self.inputs_comida["Cena"].get().strip()

        self.db.guardar_comidas(fecha, d, c, m, ce)
        
        # Feedback visual temporal en el botón
        btn = self.frame_alimentacion.winfo_children()[-1]
        btn.config(text="¡Guardado ✓!", bg='#27ae60')
        self.root.after(1500, lambda: btn.config(text="Guardar Registro Diario", bg=self.ACCENT))

    # ------------------------------------------------------------------ Avisos
    def comprobar_recordatorios(self):
        ahora = datetime.now().strftime(f'{FORMATO_FECHA} {FORMATO_HORA}')
        for id_, fecha, hora, tarea in self.db.pendientes(ahora):
            self.db.marcar_notificado(id_)
            self.root.bell()
            self.root.deiconify()
            self.root.lift()
            messagebox.showinfo('⏰ Recordatorio', f'{tarea}\n\n{fecha}  {hora}')
        self.root.after(INTERVALO_COMPROBACION_MS, self.comprobar_recordatorios)

    def cerrar(self):
        self.db.cerrar()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = AplicacionRecordatorios(root)
    root.mainloop()