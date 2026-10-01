import tkinter as tk
from tkcalendar import Calendar

def saludar():
    etiqueta.config(text="¡Botón presionado!")

root = tk.Tk()
root.title("LAL-D Record")
root.geometry("800x400")

# 2. Crear widgets
etiqueta = tk.Label(root, text="¡Hola, Tkinter!")
boton = tk.Button(root, text="Haz clic aquí", command=saludar)

# 3. Posicionar widgets
etiqueta.pack(pady=20)
boton.pack()

# 4. Iniciar aplicación
root.mainloop()