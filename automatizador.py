import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pyautogui
import time
import random
import threading
import os
import re

# Función auxiliar para escribir texto con soporte completo de acentos, tildes y eñes
def escribir_texto_con_acentos(app_instance, texto):
    tiene_caracteres_especiales = any(ord(c) > 127 for c in texto)
    if tiene_caracteres_especiales:
        try:
            app_instance.clipboard_clear()
            app_instance.clipboard_append(texto)
            app_instance.update()
            pyautogui.keyDown('ctrl')
            pyautogui.press('v')
            pyautogui.keyUp('ctrl')
            time.sleep(0.05)
        except Exception:
            pyautogui.write(texto, interval=0.03)
    else:
        pyautogui.write(texto, interval=0.03)

# Intentar importar pynput para captura global con la tecla F8
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

# Configuración de seguridad de PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# Tema visual de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TextEditorWithLineNumbers(ctk.CTkFrame):
    """Widget de editor de texto con numeración de líneas sincronizada."""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Barra lateral con número de líneas
        self.line_numbers = tk.Text(
            self,
            width=5,
            padx=3,
            pady=3,
            takefocus=0,
            border=0,
            background="#1e1e1e",
            foreground="#6e7681",
            state="disabled",
            font=("Consolas", 12),
            wrap="none"
        )
        self.line_numbers.grid(row=0, column=0, sticky="ns", padx=(2, 0), pady=2)

        # Editor de texto principal
        self.textbox = ctk.CTkTextbox(self, wrap="none", font=ctk.CTkFont(family="Consolas", size=13))
        self.textbox.grid(row=0, column=1, sticky="nsew")

        # Vincular eventos para actualizar los números de líneas
        self.textbox._textbox.bind("<KeyRelease>", self.update_line_numbers)
        self.textbox._textbox.bind("<MouseWheel>", self.update_line_numbers)
        self.textbox._textbox.bind("<Button-1>", self.update_line_numbers)
        self.textbox._textbox.bind("<Configure>", self.update_line_numbers)

        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        """Redibuja la columna de numeración de líneas según el contenido actual."""
        lines_count = int(self.textbox._textbox.index("end-1c").split(".")[0])
        line_text = "\n".join(str(i) for i in range(1, lines_count + 1))
        
        self.line_numbers.config(state="normal")
        self.line_numbers.delete("1.0", tk.END)
        self.line_numbers.insert("1.0", line_text)
        
        # Sincronizar posición de scroll vertical
        self.line_numbers.yview_moveto(self.textbox._textbox.yview()[0])
        self.line_numbers.config(state="disabled")

    def get(self, index1, index2=None):
        return self.textbox.get(index1, index2)

    def insert(self, index, text):
        res = self.textbox.insert(index, text)
        self.update_line_numbers()
        return res

    def delete(self, index1, index2=None):
        res = self.textbox.delete(index1, index2)
        self.update_line_numbers()
        return res

    def see(self, index):
        res = self.textbox.see(index)
        self.update_line_numbers()
        return res

    def focus_set(self):
        return self.textbox.focus_set()


class MacroAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Automatizador de Tareas con Editor Interactivo - Windows 11")
        self.geometry("1020x740")
        self.minsize(880, 620)

        # Variables de estado
        self.file_path = ""
        self.phrases_file_path = "frases.txt"
        self.is_running = False
        self.stop_requested = False
        self.execution_thread = None
        self.listener = None

        self.word_list = [
            "Hola mundo",
            "Automatización de Windows 11",
            "Python es genial",
            "Prueba de script automatizado",
            "Navegación rápida en Chrome",
            "Generación aleatoria de texto"
        ]
        self.active_phrases_pool = []

        self.load_phrases_from_file()
        self.create_widgets()
        
        self.update_live_mouse_coords()
        if PYNPUT_AVAILABLE:
            self.start_global_hotkey_listener()

    # --- GESTIÓN DE FRASES ALEATORIAS EN ARCHIVO PLANO ---
    def load_phrases_from_file(self):
        try:
            if os.path.exists(self.phrases_file_path):
                with open(self.phrases_file_path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        self.word_list = lines
            else:
                self.save_phrases_to_file(self.word_list)
            
            self.active_phrases_pool = list(self.word_list)
        except Exception as e:
            print(f"Error al cargar archivo de frases: {e}")

    def save_phrases_to_file(self, phrases=None):
        if phrases is None:
            raw_text = self.words_text.get("1.0", tk.END).strip()
            phrases = [line.strip() for line in raw_text.splitlines() if line.strip()]

        try:
            with open(self.phrases_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(phrases))
            self.word_list = phrases
            self.active_phrases_pool = list(self.word_list)
            self.log_status(f"Frases guardadas en '{self.phrases_file_path}'")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar 'frases.txt': {e}")

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- PANEL SUPERIOR ---
        top_frame = ctk.CTkFrame(self, corner_radius=10)
        top_frame.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        top_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top_frame, text="Archivo:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.file_entry = ctk.CTkEntry(top_frame, placeholder_text="Nuevo archivo sin guardar...")
        self.file_entry.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        ctk.CTkButton(top_frame, text="📁 Cargar", width=90, command=self.browse_file).grid(row=0, column=2, padx=5, pady=10)
        ctk.CTkButton(top_frame, text="💾 Guardar", width=90, fg_color="#1c7ed6", command=self.save_file).grid(row=0, column=3, padx=5, pady=10)
        ctk.CTkButton(top_frame, text="💾 Guardar Como", width=110, fg_color="#1c7ed6", command=self.save_file_as).grid(row=0, column=4, padx=5, pady=10)

        ctk.CTkLabel(top_frame, text="Repeticiones:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=5, padx=(15, 5), pady=10, sticky="w")
        self.repeat_spin = ctk.CTkEntry(top_frame, width=60)
        self.repeat_spin.insert(0, "1")
        self.repeat_spin.grid(row=0, column=6, padx=(0, 10), pady=10)

        # --- PANEL CENTRAL ---
        middle_frame = ctk.CTkFrame(self, corner_radius=10)
        middle_frame.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        middle_frame.grid_columnconfigure(0, weight=3)
        middle_frame.grid_columnconfigure(1, weight=2)
        middle_frame.grid_rowconfigure(1, weight=1)

        # Sub-panel Izquierdo: Editor con Numeración de Líneas
        editor_frame = ctk.CTkFrame(middle_frame, fg_color="transparent")
        editor_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky="nsew")
        editor_frame.grid_columnconfigure(0, weight=1)
        editor_frame.grid_rowconfigure(2, weight=1)

        coords_bar = ctk.CTkFrame(editor_frame)
        coords_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        coords_bar.grid_columnconfigure(0, weight=1)

        self.mouse_pos_label = ctk.CTkLabel(coords_bar, text="📍 Ratón: X: 0, Y: 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.mouse_pos_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        btn_add_coords = ctk.CTkButton(
            coords_bar, 
            text="➕ Capturar Posición (F8)", 
            fg_color="#f59f00", 
            hover_color="#d97706",
            text_color="black",
            font=ctk.CTkFont(weight="bold"),
            command=self.insert_current_mouse_position
        )
        btn_add_coords.grid(row=0, column=1, padx=10, pady=5)

        # Barra de herramientas de edición rápida
        toolbar = ctk.CTkFrame(editor_frame)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 5))

        ctk.CTkButton(toolbar, text="+ Click", width=60, command=lambda: self.insert_text_at_cursor("click(1)\n")).pack(side="left", padx=2, pady=5)
        ctk.CTkButton(toolbar, text="+ DobleClick", width=80, command=lambda: self.insert_text_at_cursor("DobleClick\n")).pack(side="left", padx=2, pady=5)
        ctk.CTkButton(toolbar, text="+ Frase Aleat.", width=85, command=lambda: self.insert_text_at_cursor("Frase Aleatoria\n")).pack(side="left", padx=2, pady=5)
        ctk.CTkButton(toolbar, text="+ Esperar 1s", width=80, command=lambda: self.insert_text_at_cursor("Esperar (Seg): 1\n")).pack(side="left", padx=2, pady=5)
        ctk.CTkButton(toolbar, text="+ NPestaña", width=75, command=lambda: self.insert_text_at_cursor("NPestaña\n")).pack(side="left", padx=2, pady=5)
        ctk.CTkButton(toolbar, text="+ Tecla Enter", width=85, command=lambda: self.insert_text_at_cursor("Tecla: Return\n")).pack(side="left", padx=2, pady=5)
        ctk.CTkButton(toolbar, text="+ Repetir", width=70, command=lambda: self.insert_text_at_cursor("Repetir: 3\n\tclick(1)\n\tEsperar (Seg): 1\n")).pack(side="left", padx=2, pady=5)
        ctk.CTkButton(toolbar, text="+ Saltar", width=65, fg_color="#ae3ec9", hover_color="#9c36b5", command=lambda: self.insert_text_at_cursor("Saltar: 1\n")).pack(side="left", padx=2, pady=5)

        # Editor de texto principal con número de líneas
        self.script_preview = TextEditorWithLineNumbers(editor_frame)
        self.script_preview.grid(row=2, column=0, sticky="nsew")

        # Sub-panel Derecho: Frases Aleatorias
        phrases_frame = ctk.CTkFrame(middle_frame, fg_color="transparent")
        phrases_frame.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")
        phrases_frame.grid_columnconfigure(0, weight=1)
        phrases_frame.grid_rowconfigure(1, weight=1)

        phrases_header = ctk.CTkFrame(phrases_frame, fg_color="transparent")
        phrases_header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        phrases_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(phrases_header, text="Frases Aleatorias (frases.txt):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w")
        btn_save_phrases = ctk.CTkButton(
            phrases_header,
            text="💾 Guardar Frases",
            width=110,
            height=24,
            fg_color="#2b8a3e",
            hover_color="#216e31",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.save_phrases_to_file
        )
        btn_save_phrases.grid(row=0, column=1, sticky="e")

        self.words_text = ctk.CTkTextbox(phrases_frame, wrap="word", font=ctk.CTkFont(size=12))
        self.words_text.grid(row=1, column=0, sticky="nsew")
        self.words_text.insert("1.0", "\n".join(self.word_list))

        # --- PANEL INFERIOR ---
        bottom_frame = ctk.CTkFrame(self, corner_radius=10)
        bottom_frame.grid(row=2, column=0, padx=15, pady=(5, 15), sticky="ew")
        bottom_frame.grid_columnconfigure(2, weight=1)

        self.btn_run = ctk.CTkButton(bottom_frame, text="▶ Ejecutar Macro", fg_color="#2b8a3e", hover_color="#216e31", font=ctk.CTkFont(size=14, weight="bold"), command=self.start_execution)
        self.btn_run.grid(row=0, column=0, padx=10, pady=12)

        self.btn_stop = ctk.CTkButton(bottom_frame, text="⏹ Detener", fg_color="#c92a2a", hover_color="#a61e1e", state="disabled", font=ctk.CTkFont(size=14, weight="bold"), command=self.stop_execution)
        self.btn_stop.grid(row=0, column=1, padx=10, pady=12)

        status_text = "Estado: Listo" if PYNPUT_AVAILABLE else "⚠️ Instale 'pynput' para activar la tecla F8 (pip install pynput)"
        self.status_label = ctk.CTkLabel(bottom_frame, text=status_text, font=ctk.CTkFont(weight="bold"), anchor="w")
        self.status_label.grid(row=0, column=2, padx=15, pady=12, sticky="ew")

    # --- MONITOREO DE RATÓN Y CAPTURA INTERACTIVA ---
    def update_live_mouse_coords(self):
        try:
            x, y = pyautogui.position()
            self.mouse_pos_label.configure(text=f"📍 Ratón: X: {x}, Y: {y}")
        except Exception:
            pass
        self.after(100, self.update_live_mouse_coords)

    def insert_current_mouse_position(self):
        x, y = pyautogui.position()
        cmd = f"Mouse: {x},{y}\n"
        self.after(0, lambda: self._append_cmd_to_editor(cmd))

    def _append_cmd_to_editor(self, text):
        try:
            current_content = self.script_preview.get("1.0", tk.END)
            if current_content and not current_content.endswith("\n") and len(current_content.strip()) > 0:
                self.script_preview.insert(tk.END, "\n")
            
            self.script_preview.insert(tk.END, text)
            self.script_preview.see(tk.END)
            self.log_status(f"Coordenada capturada: {text.strip()}")
        except Exception as e:
            print(f"Error escribiendo coordenada: {e}")

    def insert_text_at_cursor(self, text):
        try:
            self.script_preview.insert(tk.INSERT, text)
            self.script_preview.see(tk.INSERT)
            self.script_preview.focus_set()
        except Exception as e:
            print(f"Error insertando comando: {e}")

    def start_global_hotkey_listener(self):
        def on_press(key):
            try:
                is_f8 = False
                if key == keyboard.Key.f8:
                    is_f8 = True
                elif hasattr(key, 'vk') and key.vk == 119:
                    is_f8 = True
                elif hasattr(key, 'name') and key.name == 'f8':
                    is_f8 = True

                if is_f8:
                    self.after(0, self.insert_current_mouse_position)
            except Exception as e:
                print(f"Error en hotkey F8: {e}")

        try:
            self.listener = keyboard.Listener(on_press=on_press)
            self.listener.daemon = True
            self.listener.start()
        except Exception as e:
            print(f"No se pudo iniciar el escuchador global de F8: {e}")

    # --- GESTIÓN DE ARCHIVOS ---
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo de macro",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.file_path = filename
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.load_script_content(filename)

    def load_script_content(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                content = file.read()
                self.script_preview.delete("1.0", tk.END)
                self.script_preview.insert("1.0", content)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo: {e}")

    def save_file(self):
        if not self.file_path:
            self.save_file_as()
        else:
            self._write_to_file(self.file_path)

    def save_file_as(self):
        filename = filedialog.asksaveasfilename(
            title="Guardar script como",
            defaultextension=".txt",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if filename:
            self.file_path = filename
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self._write_to_file(filename)

    def _write_to_file(self, filepath):
        try:
            content = self.script_preview.get("1.0", tk.END)
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write(content)
            self.log_status(f"Guardado exitoso en '{os.path.basename(filepath)}'")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

    # --- MOTOR DE EJECUCIÓN DE MACROS ---
    def update_words_from_ui(self):
        self.save_phrases_to_file()

    def log_status(self, text):
        self.status_label.configure(text=f"Estado: {text}")

    def start_execution(self):
        script_content = self.script_preview.get("1.0", tk.END).strip()
        if not script_content:
            messagebox.showwarning("Advertencia", "El contenido del script está vacío.")
            return

        try:
            iterations = int(self.repeat_spin.get())
            if iterations <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", "El número de repeticiones debe ser un entero positivo.")
            return

        self.update_words_from_ui()

        self.is_running = True
        self.stop_requested = False
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")

        self.execution_thread = threading.Thread(
            target=self.run_macro_loop,
            args=(script_content, iterations),
            daemon=True
        )
        self.execution_thread.start()

    def stop_execution(self):
        if self.is_running:
            self.stop_requested = True
            self.log_status("Solicitando parada...")

    def run_macro_loop(self, script_text, iterations):
        raw_lines = script_text.splitlines()

        for current_iter in range(1, iterations + 1):
            if self.stop_requested:
                break

            self.log_status(f"Ejecutando iteración {current_iter} de {iterations}...")
            self.execute_script_lines(raw_lines)

        self.is_running = False
        self.stop_requested = False
        self.after(0, self.reset_ui_after_run)

    def execute_script_lines(self, lines):
        """Ejecuta una lista de líneas soportando saltos directos de línea (Saltar: N) y bloques 'Repetir'."""
        idx = 0
        total_lines = len(lines)
        max_jumps = 10000  # Prevención de bucles infinitos sin control
        jump_counter = 0

        while idx < total_lines:
            if self.stop_requested:
                break

            line = lines[idx]
            stripped_line = line.strip()

            # Ignorar líneas vacías o comentarios
            if not stripped_line or stripped_line.startswith("#"):
                idx += 1
                continue

            # Detectar orden "Saltar: N" o "Saltar a linea N"
            jump_match = re.search(r"^saltar\s*(?:a\s*l[ií]nea)?\s*:?\s*(\d+)", stripped_line, re.IGNORECASE)
            if jump_match:
                target_line = int(jump_match.group(1))
                jump_counter += 1
                if jump_counter > max_jumps:
                    print("[Aviso] Límite de saltos alcanzado para prevenir un bucle infinito.")
                    break
                
                # Convertir número de línea (1-based) a índice base 0
                target_idx = target_line - 1
                if 0 <= target_idx < total_lines:
                    idx = target_idx
                    continue
                else:
                    print(f"[Error] La línea de destino {target_line} está fuera de rango (1 - {total_lines}).")
                    idx += 1
                    continue

            # Detectar orden "Repetir"
            if stripped_line.lower().startswith("repetir"):
                match = re.search(r"repetir\s*:?\s*(\d+)", stripped_line, re.IGNORECASE)
                repeat_count = int(match.group(1)) if match else 1

                base_indent = len(line) - len(line.lstrip())

                child_lines = []
                idx += 1
                while idx < total_lines:
                    curr_line = lines[idx]
                    curr_stripped = curr_line.strip()

                    if not curr_stripped:
                        idx += 1
                        continue

                    curr_indent = len(curr_line) - len(curr_line.lstrip())
                    if curr_indent > base_indent:
                        child_lines.append(curr_line)
                        idx += 1
                    else:
                        break

                for _ in range(repeat_count):
                    if self.stop_requested:
                        break
                    self.execute_script_lines(child_lines)

            else:
                self.parse_and_execute_command(stripped_line)
                idx += 1

    def reset_ui_after_run(self):
        self.btn_run.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.log_status("Finalizado / Listo")

    def parse_and_execute_command(self, line):
        try:
            if line.startswith("Mouse:"):
                coords = line.split(":")[1].strip().split(",")
                x, y = int(coords[0]), int(coords[1])
                pyautogui.moveTo(x, y, duration=0.2)

            elif line.startswith("click"):
                match = re.search(r"click\((\d+)\)", line, re.IGNORECASE)
                clicks = int(match.group(1)) if match else 1
                pyautogui.click(clicks=clicks)

            elif line.lower() in ["dobleclick", "doble click", "doubleclick"]:
                pyautogui.doubleClick()

            elif line.lower() == "frase aleatoria":
                if not self.active_phrases_pool:
                    self.load_phrases_from_file()

                if self.active_phrases_pool:
                    selected_phrase = random.choice(self.active_phrases_pool)
                    self.active_phrases_pool.remove(selected_phrase)
                    escribir_texto_con_acentos(self, selected_phrase)

            elif line.startswith("Escribir:"):
                text_to_write = line.split(":", 1)[1].strip()
                escribir_texto_con_acentos(self, text_to_write)

            elif line.startswith("Tecla:"):
                key_name = line.split(":")[1].strip().lower()
                pyautogui.press(key_name)

            elif "esperar" in line.lower():
                match = re.search(r"(\d+(\.\d+)?)", line)
                if match:
                    seconds = float(match.group(1))
                    step = 0.1
                    elapsed = 0.0
                    while elapsed < seconds and not self.stop_requested:
                        time.sleep(step)
                        elapsed += step

            elif line.lower() in ["npestaña", "npestana", "nueva pestaña", "nuevapestaña"]:
                pyautogui.keyDown('ctrl')
                pyautogui.press('t')
                pyautogui.keyUp('ctrl')
                time.sleep(0.3)

            else:
                print(f"[Aviso] Comando no reconocido: '{line}'")

        except Exception as e:
            print(f"Error procesando comando '{line}': {e}")


if __name__ == "__main__":
    app = MacroAutomationApp()
    app.mainloop()
