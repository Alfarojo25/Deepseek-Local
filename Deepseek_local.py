import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, filedialog, ttk
import json
from datetime import datetime

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

# Instalación automática de dependencias
def instalar_dependencias():
    try:
        import openai
        import tkinter
        import fpdf
    except ImportError:
        import subprocess
        pkgs = ["openai", "fpdf"]
        for pkg in pkgs:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
        # Confirmación en settings
        settings = {}
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        settings["dependencias_instaladas"] = True
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f)

# Llama a instalar_dependencias solo la primera vez
def check_dependencias():
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            if settings.get("dependencias_instaladas"):
                return
        except Exception:
            pass
    instalar_dependencias()

check_dependencias()

def get_conversaciones_dir():
    """Obtiene la ruta de la carpeta conversaciones desde settings.json o pregunta al usuario."""
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            conversaciones_dir = settings.get("conversaciones_dir")
            if conversaciones_dir and os.path.exists(conversaciones_dir):
                return conversaciones_dir
        except Exception:
            pass
    # Pregunta al usuario y guarda en settings.json
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Instalación", "Seleccione la carpeta donde desea crear la carpeta 'conversaciones'.")
    base_dir = filedialog.askdirectory(title="Seleccione la ubicación para 'conversaciones'")
    root.destroy()
    if not base_dir:
        return None
    conversaciones_dir = os.path.join(base_dir, "conversaciones")
    if not os.path.exists(conversaciones_dir):
        try:
            os.makedirs(conversaciones_dir)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la carpeta: {e}")
            return None
    # Guarda la ruta en settings.json
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"conversaciones_dir": conversaciones_dir}, f)
    except Exception:
        pass
    return conversaciones_dir

def seleccionar_historial(conversaciones_dir):
    """Permite al usuario seleccionar el historial a cargar."""
    archivos = [f for f in os.listdir(conversaciones_dir) if f.endswith(".json")]
    if not archivos:
        # Si no hay archivos, crea uno por defecto
        nombre = simpledialog.askstring("Nuevo chat", "Nombre para la conversación:")
        if not nombre:
            nombre = "Historial_conversaciones"
        historial_path = os.path.join(conversaciones_dir, f"{nombre}.json")
        with open(historial_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        return historial_path
    # Si hay archivos, permite seleccionar uno
    root = tk.Tk()
    root.withdraw()
    seleccion = simpledialog.askstring(
        "Seleccionar conversación",
        "Conversaciones disponibles:\n" + "\n".join(f"{i+1}. {archivos[i]}" for i in range(len(archivos))) +
        "\n\nIngrese el número de la conversación a abrir, o escriba un nombre nuevo:"
    )
    root.destroy()
    if not seleccion:
        historial_path = os.path.join(conversaciones_dir, archivos[0])
    elif seleccion.isdigit() and 1 <= int(seleccion) <= len(archivos):
        historial_path = os.path.join(conversaciones_dir, archivos[int(seleccion)-1])
    else:
        # Nuevo nombre
        historial_path = os.path.join(conversaciones_dir, f"{seleccion}.json")
        if not os.path.exists(historial_path):
            with open(historial_path, "w", encoding="utf-8") as f:
                json.dump([], f)
    return historial_path

def seleccionar_ia_y_key():
    ia_opciones = ["Deepseek", "ChatGPT"]
    root = tk.Tk()
    root.title("Seleccionar IA")
    root.geometry("300x160")
    tk.Label(root, text="Elija una IA:").pack(pady=6)
    ia_var = tk.StringVar(value=ia_opciones[0])
    combo = ttk.Combobox(root, textvariable=ia_var, values=ia_opciones, state="readonly")
    combo.pack(pady=4)
    key_var = tk.StringVar()
    tk.Label(root, text="API Key:").pack()
    key_entry = tk.Entry(root, textvariable=key_var, show="*")
    key_entry.pack(pady=2)
    result = {"ia": None, "key": None}
    def confirmar():
        result["ia"] = ia_var.get()
        result["key"] = key_var.get()
        root.quit()
    btn = tk.Button(root, text="Aceptar", command=confirmar)
    btn.pack(pady=6)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
    root.destroy()
    return result["ia"], result["key"]

def get_settings():
    settings = {}
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception:
            pass
    return settings

def save_settings(settings):
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except Exception:
        pass

def get_api_key_and_ia():
    settings = get_settings()
    ia = settings.get("ia_seleccionada")
    api_keys = settings.get("api_keys", {})
    key = api_keys.get(ia)
    if not ia or not key:
        ia, key = seleccionar_ia_y_key()
        if "api_keys" not in settings:
            settings["api_keys"] = {}
        settings["api_keys"][ia] = key
        settings["ia_seleccionada"] = ia
        save_settings(settings)
    return ia, settings["api_keys"]

# === Configuración ===
BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"

def get_api_key():
    """Obtiene la API Key desde settings.json o pidiéndola al usuario y la guarda."""
    api_key = None
    # Leer settings.json si existe
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
            api_key = settings.get("deepseek_api_key")
            if api_key:
                return api_key
        except Exception:
            pass
    # Si no existe, pedir al usuario y guardar en settings.json
    root = tk.Tk()
    root.withdraw()
    api_key = simpledialog.askstring("API Key", "Ingrese su DeepSeek API Key:", show='*')
    root.destroy()
    if not api_key:
        return None
    # Guardar en settings.json junto con la carpeta de conversaciones si existe
    try:
        settings = {}
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        settings["deepseek_api_key"] = api_key
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except Exception:
        pass
    return api_key

class DeepSeekChat:
    def __init__(self, api_key, base_url, model):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.messages = [{"role": "system", "content": "Eres un asistente útil y expresivo."}]

    def stream_chat(self, user_text, callback):
        """Envía mensaje y recibe respuesta en streaming, llamando a callback con cada chunk."""
        self.messages.append({"role": "user", "content": user_text})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True
        )

        reply_accum = ""
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                reply_accum += delta.content
                callback(delta.content)
        self.messages.append({"role": "assistant", "content": reply_accum})
        return reply_accum

class ChatApp:
    def __init__(self, parent, bot, historial_path, notebook=None, tab_frame=None, ia_tipo="Deepseek", api_keys=None):
        self.parent = parent
        self.bot = bot
        self.historial_path = historial_path
        self.notebook = notebook
        self.tab_frame = tab_frame
        self.history = []
        self._in_streaming = False
        self.last_reply = ""
        self.replies = []
        self.reply_label = None
        self.renombrado = False  # Para saber si ya renombró el archivo y la pestaña
        self.titulo = None
        self.ia_tipo = ia_tipo
        self.api_keys = api_keys

        # Frame principal para la pestaña
        self.frame = tk.Frame(parent)
        self.frame.pack(fill="both", expand=True)

        # Área de chat
        self.chat_frame = tk.Frame(self.frame)
        self.chat_frame.pack(padx=10, pady=10, fill="both", expand=True)
        self.chat_canvas = tk.Canvas(self.chat_frame)
        self.scrollbar = tk.Scrollbar(self.chat_frame, orient="vertical", command=self.chat_canvas.yview)
        self.scrollable_frame = tk.Frame(self.chat_canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.chat_canvas.configure(
                scrollregion=self.chat_canvas.bbox("all")
            )
        )
        self.chat_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.chat_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.chat_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Entrada + botones
        entry_frame = tk.Frame(self.frame)
        self.input_text = tk.Text(entry_frame, height=4, wrap="word", font=("Segoe UI", 10))
        self.input_text.pack(side="left", padx=(0, 6), fill="x", expand=True)
        send_btn = tk.Button(entry_frame, text="Enviar", width=10, command=self.on_send)
        send_btn.pack(side="right")
        entry_frame.pack(padx=10, pady=(0, 6), fill="x")

        # Estado
        self.status_var = tk.StringVar(value="Listo.")
        status_label = tk.Label(self.frame, textvariable=self.status_var, anchor="w")
        status_label.pack(fill="x", padx=10, pady=(0, 6))

        # Actualiza el ancho de los labels al cambiar el tamaño de la pestaña
        self.frame.bind("<Configure>", self._update_wraplength)
        self.label_widgets = []

        self.load_history()
        # Establece el título de la pestaña si existe en el json
        if self.notebook is not None and self.tab_frame is not None:
            if self.titulo:
                self.notebook.tab(self.tab_frame, text=self.titulo)

    def load_history(self):
        """Carga historial desde archivo y lo muestra en el chat. Si no existe, lo crea vacío."""
        self.history = []
        self.titulo = None
        if os.path.exists(self.historial_path):
            try:
                with open(self.historial_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.titulo = loaded.get("titulo")
                        mensajes = loaded.get("mensajes", [])
                    elif isinstance(loaded, list):
                        mensajes = loaded
                    else:
                        mensajes = []
                    for msg in mensajes:
                        if isinstance(msg, dict) and "author" in msg and "text" in msg:
                            fecha_hora = msg.get("fecha_hora")
                            self.history.append(msg)
                            self.append_chat(msg["author"], msg["text"], add_to_history=False, fecha_hora=fecha_hora)
            except Exception as e:
                messagebox.showwarning("Historial", f"No se pudo cargar el historial: {e}")
                self.history = []
        else:
            # Si no existe, crea el archivo vacío con estructura nueva
            try:
                with open(self.historial_path, "w", encoding="utf-8") as f:
                    json.dump({"titulo": None, "mensajes": []}, f)
            except Exception as e:
                messagebox.showwarning("Historial", f"No se pudo crear el historial: {e}")
            self.history = []

    def save_history(self):
        """Guarda historial en archivo JSON."""
        try:
            with open(self.historial_path, "w", encoding="utf-8") as f:
                json.dump({"titulo": self.titulo, "mensajes": self.history}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showwarning("Historial", f"No se pudo guardar el historial: {e}")

    def append_chat(self, author, text, tag=None, add_to_history=True, fecha_hora=None):
        frame = tk.Frame(self.scrollable_frame, pady=2)
        max_length = 4096
        display_text = text[:max_length] + ("..." if len(text) > max_length else "")
        # Fecha y hora
        if fecha_hora is None:
            fecha_hora = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        user_frame = tk.Frame(frame)
        user_label = tk.Label(user_frame, text=author, font=("Segoe UI", 10, "bold"))
        user_label.pack(side="left")
        fecha_label = tk.Label(user_frame, text=fecha_hora, font=("Segoe UI", 8), bg="#e0e0e0", fg="#444", padx=6, pady=1)
        fecha_label.pack(side="left", padx=(6,0))
        # Botón copiar al lado de la fecha
        if author == "DeepSeek" or author == "ChatGPT":
            copy_btn = tk.Button(user_frame, text="📋 Copiar", command=lambda t=text: self.copy_message(t))
            copy_btn.pack(side="left", padx=(6,0))
        user_frame.pack(anchor="w")
        # Mensaje
        if author == "DeepSeek" or author == "ChatGPT":
            label = tk.Label(frame, text=display_text, anchor="w", font=("Segoe UI Emoji", 10),
                             bg="#f0f0ff", justify="left", wraplength=self.frame.winfo_width())
            label.pack(side="top", fill="x", expand=True)
            self.label_widgets.append(label)
            self.replies.append(text)
        else:
            label = tk.Label(frame, text=display_text, anchor="w", font=("Segoe UI", 10),
                             justify="left", wraplength=self.frame.winfo_width())
            label.pack(side="top", fill="x", expand=True)
            self.label_widgets.append(label)
        frame.pack(fill="x", padx=2, pady=2)
        self.chat_canvas.yview_moveto(1)
        if add_to_history:
            self.history.append({"author": author, "text": text, "fecha_hora": fecha_hora})

        # Renombrar el archivo y la pestaña con cada pregunta del usuario
        if author == "Tú" and self.notebook is not None and self.tab_frame is not None:
            texto_original = text.strip()[:40]
            nombre = texto_original.replace(" ", "_")
            nombre = "".join(c for c in nombre if c.isalnum() or c in ("_", "-"))
            if not nombre:
                nombre = "Chat"
                texto_original = "Chat"
            nuevo_json = os.path.join(os.path.dirname(self.historial_path), f"{nombre}.json")
            base_nombre = nombre
            base_texto = texto_original
            sufijo = 1
            while os.path.exists(nuevo_json):
                nombre = f"{base_nombre}_{sufijo}"
                texto_original = f"{base_texto} {sufijo}"
                nuevo_json = os.path.join(os.path.dirname(self.historial_path), f"{nombre}.json")
                sufijo += 1
            try:
                os.rename(self.historial_path, nuevo_json)
                self.historial_path = nuevo_json
            except Exception as e:
                messagebox.showwarning("Renombrar", f"No se pudo renombrar el historial: {e}")
            # Guarda el título original en el json y actualiza la pestaña
            self.titulo = texto_original
            self.notebook.tab(self.tab_frame, text=texto_original)
        self.chat_canvas.yview_moveto(1)

    def start_reply(self, author):
        self._in_streaming = True
        self.last_reply = ""
        self.reply_frame = tk.Frame(self.scrollable_frame, pady=2)
        reply_user_frame = tk.Frame(self.reply_frame)
        fecha_hora = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        reply_label = tk.Label(reply_user_frame, text=f"{author}", font=("Segoe UI", 10, "bold"))
        reply_label.pack(side="left")
        fecha_label = tk.Label(reply_user_frame, text=fecha_hora, font=("Segoe UI", 8), bg="#e0e0e0", fg="#444", padx=6, pady=1)
        fecha_label.pack(side="left", padx=(6,0))
        self.reply_copy_btn = tk.Button(reply_user_frame, text="📋 Copiar", command=lambda: self.copy_message(self.last_reply))
        self.reply_copy_btn.pack(side="left", padx=(6,0))
        reply_user_frame.pack(anchor="w")
        self.reply_label = tk.Label(self.reply_frame, text="", anchor="w", font=("Segoe UI Emoji", 10),
                                   bg="#f0f0ff", justify="left", wraplength=self.frame.winfo_width())
        self.reply_label.pack(side="top", fill="x", expand=True)
        self.reply_frame.pack(fill="x", padx=2, pady=2)
        self.chat_canvas.yview_moveto(1)

    def update_reply(self, text):
        max_length = 4096
        if self._in_streaming and self.reply_label:
            current = self.reply_label.cget("text")
            new_text = (current + text)[:max_length]
            self.reply_label.config(text=new_text + ("..." if len(current + text) > max_length else ""))
            self.last_reply = new_text
            self.chat_canvas.update_idletasks()
            self.chat_canvas.yview_moveto(1)

    def end_reply(self):
        if self._in_streaming and self.reply_label:
            self.reply_label.config(text=self.reply_label.cget("text") + "\n\n")
            self._in_streaming = False
            self.replies.append(self.last_reply)
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history.append({"author": self.ia_tipo, "text": self.last_reply, "fecha_hora": fecha_hora})

    def on_send(self):
        """Envía el mensaje del usuario y lanza el hilo para la respuesta."""
        user_text = self.input_text.get("1.0", tk.END).strip()
        if not user_text:
            return
        self.input_text.delete("1.0", tk.END)
        self.append_chat("Tú", user_text)  # fecha_hora se agrega automáticamente
        threading.Thread(target=self.get_reply, args=(user_text,), daemon=True).start()

    def get_reply(self, user_text):
        try:
            self.status_var.set("Respondiendo...")
            self.start_reply("DeepSeek" if self.ia_tipo == "Deepseek" else self.ia_tipo)
            max_length = 4096
            if self.ia_tipo == "Deepseek":
                reply = self.bot.stream_chat(user_text, self.update_reply)
                reply = reply[:max_length] + ("..." if len(reply) > max_length else "")
                self.end_reply()
                self.last_reply = reply
            elif self.ia_tipo == "ChatGPT":
                from openai import OpenAI
                api_key = self.api_keys.get("ChatGPT")
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "user", "content": user_text},
                    ]
                )
                reply = response.choices[0].message.content
                reply = reply[:max_length] + ("..." if len(reply) > max_length else "")
                self.update_reply(reply)
                self.end_reply()
                self.last_reply = reply
            self.status_var.set("Listo.")
        except Exception as e:
            self.append_chat("Error", str(e))
            self.status_var.set("Error en la petición.")

    def copy_message(self, text):
        """Copia al portapapeles el mensaje dado."""
        if text:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(text)
            self.parent.update()
            messagebox.showinfo("Copiado", "Mensaje copiado al portapapeles ✅")
        else:
            messagebox.showwarning("Aviso", "No hay ningún mensaje para copiar.")

    def on_close(self):
        """Guarda historial (sin cerrar la ventana principal)."""
        self.save_history()
        # Elimina: self.parent.destroy()

    def _update_wraplength(self, event):
        # Ajusta el wraplength de todos los labels al ancho actual de la pestaña
        new_wrap = event.width - 40 if event.width > 100 else 100
        for label in self.label_widgets:
            label.config(wraplength=new_wrap)
        # También ajusta el reply_label si existe
        if self.reply_label:
            self.reply_label.config(wraplength=new_wrap)

def main():
    ia, api_keys = get_api_key_and_ia()
    api_key = api_keys.get(ia)
    if not api_key:
        messagebox.showerror("Error", "No se ingresó una API Key.")
        return

    def crear_bot(ia, api_keys):
        if ia == "Deepseek":
            base_url = "https://api.deepseek.com"
            model = "deepseek-chat"
            return DeepSeekChat(api_keys["Deepseek"], base_url, model)
        elif ia == "ChatGPT":
            # No se usa DeepSeekChat, solo se pasa la key
            return None
        elif ia == "Copilot":
            # No se usa DeepSeekChat, solo se pasa la key
            return None
        else:
            base_url = "https://api.deepseek.com"
            model = "deepseek-chat"
            return DeepSeekChat(api_keys["Deepseek"], base_url, model)

    bot = crear_bot(ia, api_keys)

    conversaciones_dir = get_conversaciones_dir()
    if not conversaciones_dir:
        messagebox.showerror("Error", "No se seleccionó ninguna carpeta para conversaciones.")
        return

    archivos = [f for f in os.listdir(conversaciones_dir) if f.endswith(".json")]
    if not archivos:
        idx = 1
        while True:
            nuevo_nombre = f"Chat_nuevo_{idx}.json"
            historial_path = os.path.join(conversaciones_dir, nuevo_nombre)
            if not os.path.exists(historial_path):
                with open(historial_path, "w", encoding="utf-8") as f:
                    json.dump([], f)
                archivos = [nuevo_nombre]
                break
            idx += 1
    root = tk.Tk()
    root.title("DeepSeek Chat (Streaming)")

    menubar = tk.Menu(root)
    usuario_menu = tk.Menu(menubar, tearoff=0)
    usuario_menu.add_command(label="Perfil de usuario", command=lambda: messagebox.showinfo("Usuario", "Función de perfil de usuario"))
    menubar.add_cascade(label="Usuario", menu=usuario_menu)

    def seleccionar_ia_desde_menu(ia_seleccionada):
        settings = get_settings()
        api_keys = settings.get("api_keys", {})
        key = api_keys.get(ia_seleccionada)
        if not key:
            key = simpledialog.askstring("API Key", f"Ingrese la API Key para {ia_seleccionada}:", show='*')
            if "api_keys" not in settings:
                settings["api_keys"] = {}
            settings["api_keys"][ia_seleccionada] = key
            save_settings(settings)
        settings["ia_seleccionada"] = ia_seleccionada
        save_settings(settings)
        for app in chat_apps:
            app.ia_tipo = ia_seleccionada
            app.api_keys = settings["api_keys"]
            if ia_seleccionada == "Deepseek":
                app.bot = crear_bot("Deepseek", settings["api_keys"])
            else:
                app.bot = None
        messagebox.showinfo("IA", f"IA seleccionada: {ia_seleccionada}\nKey guardada.")

    ia_menu = tk.Menu(menubar, tearoff=0)
    ia_menu.add_command(label="Deepseek", command=lambda: seleccionar_ia_desde_menu("Deepseek"))
    ia_menu.add_command(label="ChatGPT", command=lambda: seleccionar_ia_desde_menu("ChatGPT"))
    menubar.add_cascade(label="IA Prompt", menu=ia_menu)

    def actualizar_key():
        ia_opciones = ["Deepseek", "ChatGPT"]
        root_cfg = tk.Toplevel(root)
        root_cfg.title("Actualizar Key")
        root_cfg.geometry("300x160")
        tk.Label(root_cfg, text="Seleccione la IA:").pack(pady=6)
        ia_var = tk.StringVar(value=ia_opciones[0])
        combo = ttk.Combobox(root_cfg, textvariable=ia_var, values=ia_opciones, state="readonly")
        combo.pack(pady=4)
        key_var = tk.StringVar()
        tk.Label(root_cfg, text="Nueva API Key:").pack()
        key_entry = tk.Entry(root_cfg, textvariable=key_var, show="*")
        key_entry.pack(pady=2)
        def confirmar():
            ia_sel = ia_var.get()
            nueva_key = key_var.get()
            settings = get_settings()
            if "api_keys" not in settings:
                settings["api_keys"] = {}
            settings["api_keys"][ia_sel] = nueva_key
            save_settings(settings)
            for app in chat_apps:
                app.api_keys = settings["api_keys"]
                if app.ia_tipo == ia_sel and ia_sel == "Deepseek":
                    app.bot = crear_bot("Deepseek", settings["api_keys"])
            messagebox.showinfo("Configuración", f"Key de {ia_sel} actualizada.")
            root_cfg.destroy()
        btn = tk.Button(root_cfg, text="Actualizar", command=confirmar)
        btn.pack(pady=6)
        root_cfg.protocol("WM_DELETE_WINDOW", root_cfg.destroy)
        root_cfg.mainloop()

    ajustes_menu = tk.Menu(menubar, tearoff=0)
    ajustes_menu.add_separator()
    ajustes_menu.add_command(label="Actualizar Key", command=actualizar_key)
    ajustes_menu.add_command(label="Configuración", command=lambda: messagebox.showinfo("Ajustes", "Función de configuración"))
    menubar.add_cascade(label="Ajustes", menu=ajustes_menu)
    root.config(menu=menubar)

    # Frame para los botones de pestañas
    tabs_btn_frame = tk.Frame(root)
    tabs_btn_frame.pack(fill="x", pady=4)

    def crear_nuevo_chat():
        idx = 1
        while True:
            nuevo_nombre = f"Chat_nuevo_{idx}.json"
            historial_path = os.path.join(conversaciones_dir, nuevo_nombre)
            if not os.path.exists(historial_path):
                with open(historial_path, "w", encoding="utf-8") as f:
                    json.dump([], f)
                break
            idx += 1
        # Usa la IA y key actual
        current_settings = get_settings()
        ia_actual = current_settings.get("ia_seleccionada", "Deepseek")
        api_keys_actual = current_settings.get("api_keys", {})
        bot_actual = crear_bot(ia_actual, api_keys_actual)
        chat_app = ChatApp(notebook, bot_actual, historial_path, notebook, None, ia_tipo=ia_actual, api_keys=api_keys_actual)
        tab_text = "Chat nuevo"
        tab_frame = chat_app.frame

        notebook.add(tab_frame, text=tab_text)
        chat_app.tab_frame = tab_frame
        chat_apps.append(chat_app)
        tab_frames.append(tab_frame)
        notebook.select(tab_frame)

    def cerrar_pestana_actual():
        idx = notebook.index(notebook.select())
        if idx >= 0 and idx < len(chat_apps):
            close_tab(idx)

    nuevo_btn = tk.Button(tabs_btn_frame, text="➕ Nuevo chat", command=crear_nuevo_chat)
    nuevo_btn.pack(side="left", padx=(10, 6))
    cerrar_btn = tk.Button(tabs_btn_frame, text="✖ Cerrar pestaña", command=cerrar_pestana_actual)
    cerrar_btn.pack(side="left", padx=(0, 10))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    chat_apps = []
    tab_frames = []

    def close_tab(idx):
        app = chat_apps[idx]
        app.save_history()
        try:
            if os.path.exists(app.historial_path):
                os.remove(app.historial_path)
        except Exception as e:
            messagebox.showwarning("Eliminar historial", f"No se pudo eliminar el historial: {e}")
        notebook.forget(tab_frames[idx])
        del chat_apps[idx]
        del tab_frames[idx]

    for i, archivo in enumerate(archivos):
        historial_path = os.path.join(conversaciones_dir, archivo)
        chat_app = ChatApp(notebook, bot, historial_path, notebook, None, ia_tipo=ia, api_keys=api_keys)
        tab_frame = chat_app.frame
        tab_text = chat_app.titulo if chat_app.titulo else archivo.replace(".json", "")

        notebook.add(tab_frame, text=tab_text)
        chat_app.tab_frame = tab_frame
        chat_apps.append(chat_app)
        tab_frames.append(tab_frame)

    def on_main_close():
        for app in chat_apps:
            app.save_history()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_main_close)

    root.mainloop()

if __name__ == "__main__":
    main()