import sys
import sqlite3
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QCalendarWidget, QListWidget, QLineEdit, 
                             QTimeEdit, QPushButton, QMessageBox)
from PyQt6.QtCore import QDate, QTime

class AplicacionRecordatorios(QWidget):
    def __init__(self):
        super().__init__()
        self.inicializar_base_datos()
        self.configurar_interfaz()
        # Cargar las tareas del día actual al iniciar
        self.actualizar_lista_tareas()

    def inicializar_base_datos(self):
        # Conecta o crea el archivo SQLite automáticamente
        self.conn = sqlite3.connect('mis_recordatorios.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS recordatorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                tarea TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def configurar_interfaz(self):
        self.setWindowTitle('Calendario y Recordatorios')
        self.resize(500, 600)

        # Layout principal (vertical)
        layout_principal = QVBoxLayout()

        # 1. Widget de Calendario
        self.calendario = QCalendarWidget()
        self.calendario.setGridVisible(True)
        self.calendario.selectionChanged.connect(self.actualizar_lista_tareas)
        layout_principal.addWidget(self.calendario)

        # 2. Lista de Tareas para el día seleccionado
        self.lista_tareas = QListWidget()
        layout_principal.addWidget(self.lista_tareas)

        # 3. Formulario para añadir nueva tarea (Layout horizontal)
        layout_formulario = QHBoxLayout()
        
        self.input_hora = QTimeEdit()
        self.input_hora.setTime(QTime.currentTime())
        layout_formulario.addWidget(self.input_hora)

        self.input_tarea = QLineEdit()
        self.input_tarea.setPlaceholderText('Escribe un nuevo recordatorio...')
        layout_formulario.addWidget(self.input_tarea)

        boton_añadir = QPushButton('Añadir')
        boton_añadir.clicked.connect(self.añadir_tarea)
        layout_formulario.addWidget(boton_añadir)

        layout_principal.addLayout(layout_formulario)

        # Aplicar el layout a la ventana
        self.setLayout(layout_principal)

    def añadir_tarea(self):
        fecha = self.calendario.selectedDate().toString('yyyy-MM-dd')
        hora = self.input_hora.time().toString('HH:mm')
        tarea = self.input_tarea.text().strip()

        if not tarea:
            QMessageBox.warning(self, 'Error', 'La descripción del recordatorio no puede estar vacía.')
            return

        # Insertar en la base de datos SQLite
        self.cursor.execute('INSERT INTO recordatorios (fecha, hora, tarea) VALUES (?, ?, ?)', 
                            (fecha, hora, tarea))
        self.conn.commit()

        self.input_tarea.clear()
        self.actualizar_lista_tareas()

    def actualizar_lista_tareas(self):
        self.lista_tareas.clear()
        fecha_seleccionada = self.calendario.selectedDate().toString('yyyy-MM-dd')

        # Consultar la base de datos para la fecha seleccionada
        self.cursor.execute('SELECT hora, tarea FROM recordatorios WHERE fecha = ? ORDER BY hora', 
                            (fecha_seleccionada,))
        registros = self.cursor.fetchall()

        if registros:
            for hora, tarea in registros:
                self.lista_tareas.addItem(f"{hora} - {tarea}")
        else:
            self.lista_tareas.addItem("No hay recordatorios para este día.")

    def closeEvent(self, event):
        # Cerrar la conexión a la base de datos al salir
        self.conn.close()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ventana = AplicacionRecordatorios()
    ventana.show()
    sys.exit(app.exec())