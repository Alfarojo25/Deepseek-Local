import os
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox, filedialog, ttk
from openai import OpenAI
import json

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

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
    def __init__(self, api_key, base_url=BASE_URL, model=DEFAULT_MODEL):
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
    def __init__(self, parent, bot: DeepSeekChat, historial_path, notebook=None, tab_frame=None):
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
                            self.history.append(msg)
                            self.append_chat(msg["author"], msg["text"], add_to_history=False)
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

    def append_chat(self, author, text, tag=None, add_to_history=True):
        """Agrega un bloque completo al chat."""
        frame = tk.Frame(self.scrollable_frame, pady=2)
        max_length = 2000  # Limite de caracteres por mensaje visualizado
        display_text = text[:max_length] + ("..." if len(text) > max_length else "")
        if author == "DeepSeek":
            label = tk.Label(frame, text=display_text, anchor="w", font=("Segoe UI Emoji", 10),
                             bg="#f0f0ff", justify="left", wraplength=self.frame.winfo_width())
            label.pack(side="left", fill="x", expand=True)
            self.label_widgets.append(label)
            copy_btn = tk.Button(frame, text="📋 Copiar", command=lambda t=text: self.copy_message(t))
            copy_btn.pack(side="right", padx=4)
            self.replies.append(text)
        else:
            label = tk.Label(frame, text=f"{author}: {display_text}", anchor="w", font=("Segoe UI", 10),
                             justify="left", wraplength=self.frame.winfo_width())
            label.pack(side="left", fill="x", expand=True)
            self.label_widgets.append(label)
        frame.pack(fill="x", padx=2, pady=2)
        self.chat_canvas.yview_moveto(1)
        if add_to_history:
            self.history.append({"author": author, "text": text})

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
        # ...existing code...
        self.chat_canvas.yview_moveto(1)
        if add_to_history:
            self.history.append({"author": author, "text": text})

        # Renombrar el archivo y la pestaña si es la primera pregunta del usuario en un chat nuevo
        if (author == "Tú" and not self.renombrado and len(self.history) == 1
            and self.notebook is not None and self.tab_frame is not None):
            # Sanitiza el texto para nombre de archivo
            nombre = text.strip().replace(" ", "_")[:40]
            nombre = "".join(c for c in nombre if c.isalnum() or c in ("_", "-"))
            if not nombre:
                nombre = "Chat"
            nuevo_json = os.path.join(os.path.dirname(self.historial_path), f"{nombre}.json")
            # Renombra el archivo físico
            try:
                os.rename(self.historial_path, nuevo_json)
                self.historial_path = nuevo_json
            except Exception as e:
                messagebox.showwarning("Renombrar", f"No se pudo renombrar el historial: {e}")
            # Renombra la pestaña
            idx = self.notebook.tabs().index(str(self.tab_frame))
            self.notebook.tab(self.tab_frame, text=nombre)
            self.renombrado = True

    def start_reply(self, author):
        """Crea un bloque vacío para rellenar durante el streaming."""
        self._in_streaming = True
        self.last_reply = ""
        self.reply_frame = tk.Frame(self.scrollable_frame, pady=2)
        self.reply_label = tk.Label(self.reply_frame, text=f"{author}: ", anchor="w", font=("Segoe UI Emoji", 10), bg="#f0f0ff", justify="left", wraplength=650)
        self.reply_label.pack(side="left", fill="x", expand=True)
        self.reply_copy_btn = tk.Button(self.reply_frame, text="📋 Copiar", command=lambda: self.copy_message(self.last_reply))
        self.reply_copy_btn.pack(side="right", padx=4)
        self.reply_frame.pack(fill="x", padx=2, pady=2)
        self.chat_canvas.yview_moveto(1)

    def update_reply(self, text):
        """Agrega texto al final de la última respuesta en streaming."""
        if self._in_streaming and self.reply_label:
            current = self.reply_label.cget("text")
            self.reply_label.config(text=current + text)
            self.last_reply += text
            self.chat_canvas.update_idletasks()
            self.chat_canvas.yview_moveto(1)  # <-- scroll automático al final

    def end_reply(self):
        """Finaliza un bloque de streaming."""
        if self._in_streaming and self.reply_label:
            self.reply_label.config(text=self.reply_label.cget("text") + "\n\n")
            self._in_streaming = False
            self.replies.append(self.last_reply)
            # Agrega el mensaje completo al historial
            self.history.append({"author": "DeepSeek", "text": self.last_reply})

    def on_send(self):
        """Envía el mensaje del usuario y lanza el hilo para la respuesta."""
        user_text = self.input_text.get("1.0", tk.END).strip()
        if not user_text:
            return
        self.input_text.delete("1.0", tk.END)
        self.append_chat("Tú", user_text)
        threading.Thread(target=self.get_reply, args=(user_text,), daemon=True).start()

    def get_reply(self, user_text):
        try:
            self.status_var.set("Respondiendo...")
            self.start_reply("DeepSeek")
            reply = self.bot.stream_chat(user_text, self.update_reply)
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

def main():
    api_key = get_api_key()
    if not api_key:
        messagebox.showerror("Error", "No se ingresó una API Key de DeepSeek.")
        return

    conversaciones_dir = get_conversaciones_dir()
    if not conversaciones_dir:
        messagebox.showerror("Error", "No se seleccionó ninguna carpeta para conversaciones.")
        return

    archivos = [f for f in os.listdir(conversaciones_dir) if f.endswith(".json")]
    if not archivos:
        # Si no hay archivos, crea uno totalmente nuevo con nombre incremental
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
        chat_app = ChatApp(notebook, bot, historial_path, notebook, None)
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

    bot = DeepSeekChat(api_key)
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
        chat_app = ChatApp(notebook, bot, historial_path, notebook, None)
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