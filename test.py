import sys
from PyQt6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
ventana = QLabel("¡Hola, la ventana funciona!")
ventana.show()
sys.exit(app.exec())