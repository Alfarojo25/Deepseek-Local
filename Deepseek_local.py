import os
import sys
import threading
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QPushButton, QLabel, 
                            QScrollArea, QFrame, QTabWidget, QMenuBar, QDialog, 
                            QComboBox, QLineEdit, QDialogButtonBox, QMessageBox,
                            QFileDialog, QInputDialog, QCheckBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QClipboard

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "settings.json")

# Instalación automática de dependencias
def instalar_dependencias():
    try:
        import openai
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
            json.dump(settings, f, ensure_ascii=False, indent=2)

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
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    QMessageBox.information(None, "Instalación", "Seleccione la carpeta donde desea crear la carpeta 'conversaciones'.")
    base_dir = QFileDialog.getExistingDirectory(None, "Seleccione la ubicación para 'conversaciones'")
    
    if not base_dir:
        return None
    conversaciones_dir = os.path.join(base_dir, "conversaciones")
    if not os.path.exists(conversaciones_dir):
        try:
            os.makedirs(conversaciones_dir)
        except Exception as e:
            QMessageBox.critical(None, "Error", f"No se pudo crear la carpeta: {e}")
            return None
    # Guarda la ruta en settings.json
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump({"conversaciones_dir": conversaciones_dir}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return conversaciones_dir

def seleccionar_historial(conversaciones_dir):
    """Permite al usuario seleccionar el historial a cargar."""
    archivos = [f for f in os.listdir(conversaciones_dir) if f.endswith(".json")]
    if not archivos:
        # Si no hay archivos, crea uno por defecto
        nombre, ok = QInputDialog.getText(None, "Nuevo chat", "Nombre para la conversación:")
        if not ok or not nombre:
            nombre = "Historial_conversaciones"
        historial_path = os.path.join(conversaciones_dir, f"{nombre}.json")
        with open(historial_path, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return historial_path
    # Si hay archivos, permite seleccionar uno
    opciones = "\n".join(f"{i+1}. {archivos[i]}" for i in range(len(archivos)))
    seleccion, ok = QInputDialog.getText(
        None, "Seleccionar conversación",
        f"Conversaciones disponibles:\n{opciones}\n\nIngrese el número de la conversación a abrir, o escriba un nombre nuevo:"
    )
    if not ok or not seleccion:
        historial_path = os.path.join(conversaciones_dir, archivos[0])
    elif seleccion.isdigit() and 1 <= int(seleccion) <= len(archivos):
        historial_path = os.path.join(conversaciones_dir, archivos[int(seleccion)-1])
    else:
        # Nuevo nombre
        historial_path = os.path.join(conversaciones_dir, f"{seleccion}.json")
        if not os.path.exists(historial_path):
            with open(historial_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    return historial_path

class IASelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar IA")
        self.setFixedSize(300, 160)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Elija una IA:"))
        
        self.ia_combo = QComboBox()
        self.ia_combo.addItems(["Deepseek", "ChatGPT"])
        layout.addWidget(self.ia_combo)
        
        layout.addWidget(QLabel("API Key:"))
        
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_values(self):
        return self.ia_combo.currentText(), self.key_input.text()

def seleccionar_ia_y_key():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    dialog = IASelectionDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_values()
    return None, None

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
            json.dump(settings, f, ensure_ascii=False, indent=2)
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
    api_key, ok = QInputDialog.getText(None, "API Key", "Ingrese su DeepSeek API Key:", QLineEdit.EchoMode.Password)
    if not ok or not api_key:
        return None
    # Guardar en settings.json junto con la carpeta de conversaciones si existe
    try:
        settings = {}
        if os.path.exists(SETTINGS_PATH):
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        settings["deepseek_api_key"] = api_key
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
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

class ChatStreamThread(QThread):
    chunk_received = pyqtSignal(str)
    finished_streaming = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, bot, user_text, ia_tipo, api_keys):
        super().__init__()
        self.bot = bot
        self.user_text = user_text
        self.ia_tipo = ia_tipo
        self.api_keys = api_keys
        self.full_reply = ""
    
    def run(self):
        try:
            max_length = 4096
            if self.ia_tipo == "Deepseek":
                self.full_reply = self.bot.stream_chat(self.user_text, self.emit_chunk)
                self.full_reply = self.full_reply[:max_length] + ("..." if len(self.full_reply) > max_length else "")
            elif self.ia_tipo == "ChatGPT":
                from openai import OpenAI
                api_key = self.api_keys.get("ChatGPT")
                client = OpenAI(api_key=api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "user", "content": self.user_text},
                    ]
                )
                reply = response.choices[0].message.content
                reply = reply[:max_length] + ("..." if len(reply) > max_length else "")
                self.full_reply = reply
                self.emit_chunk(reply)
            
            self.finished_streaming.emit(self.full_reply)
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def emit_chunk(self, chunk):
        self.chunk_received.emit(chunk)

class ChatWidget(QWidget):
    def __init__(self, bot, historial_path, parent_tabs=None, ia_tipo="Deepseek", api_keys=None, parent=None):
        super().__init__(parent)
        self.bot = bot
        self.historial_path = historial_path
        self.parent_tabs = parent_tabs
        self.history = []
        self._in_streaming = False
        self.last_reply = ""
        self.replies = []
        self.reply_widget = None
        self.renombrado = False
        self.titulo = None
        self.ia_tipo = ia_tipo
        self.api_keys = api_keys
        self.stream_thread = None
        
        self.init_ui()
        self.load_history()
        
        if self.parent_tabs is not None and self.titulo:
            # Encuentra el índice de esta pestaña y actualiza el título
            for i in range(self.parent_tabs.count()):
                if self.parent_tabs.widget(i) == self:
                    self.parent_tabs.setTabText(i, self.titulo)
                    break
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Área de chat con scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #1e1e1e; border: none; }")
        
        self.chat_widget = QWidget()
        self.chat_widget.setStyleSheet("QWidget { background-color: #1e1e1e; }")
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.chat_widget)
        layout.addWidget(self.scroll_area)
        
        # Entrada de texto y botón de envío
        input_layout = QHBoxLayout()
        
        self.input_text = QTextEdit()
        self.input_text.setMaximumHeight(100)
        self.input_text.setFont(QFont("Segoe UI", 10))
        self.input_text.setStyleSheet("QTextEdit { background-color: #2d2d2d; color: white; border: 2px solid #555555; border-radius: 5px; padding: 5px; }")
        # Conectar eventos para auto-scroll durante escritura
        self.input_text.textChanged.connect(self.on_text_changed)
        self.input_text.cursorPositionChanged.connect(self.on_cursor_moved)
        input_layout.addWidget(self.input_text)
        
        self.send_button = QPushButton("Enviar")
        self.send_button.setFixedWidth(100)
        self.send_button.setStyleSheet("QPushButton { background-color: #0d7377; color: white; border: none; border-radius: 5px; padding: 8px; font-weight: bold; } QPushButton:hover { background-color: #14a085; }")
        self.send_button.clicked.connect(self.on_send)
        input_layout.addWidget(self.send_button)
        
        layout.addLayout(input_layout)
        
        # Estado
        self.status_label = QLabel("Listo.")
        self.status_label.setStyleSheet("QLabel { color: #cccccc; padding: 5px; }")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Aplicar tema oscuro al widget principal
        self.setStyleSheet("QWidget { background-color: #1e1e1e; color: white; }")
    
    def load_history(self):
        """Carga historial desde archivo y lo muestra en el chat."""
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
                QMessageBox.warning(self, "Historial", f"No se pudo cargar el historial: {e}")
                self.history = []
        else:
            # Si no existe, crea el archivo vacío con estructura nueva
            try:
                with open(self.historial_path, "w", encoding="utf-8") as f:
                    json.dump({"titulo": None, "mensajes": []}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                QMessageBox.warning(self, "Historial", f"No se pudo crear el historial: {e}")
            self.history = []
    
    def apply_theme(self, styles):
        """Aplica un tema específico a este widget de chat"""
        # Aplicar estilo al widget principal
        self.setStyleSheet(f"QWidget {{ background-color: {styles['main_bg']}; color: {styles['text_color']}; }}")
        
        # Aplicar estilo al área de scroll
        self.scroll_area.setStyleSheet(f"QScrollArea {{ background-color: {styles['chat_bg']}; border: none; }}")
        self.chat_widget.setStyleSheet(f"QWidget {{ background-color: {styles['chat_bg']}; }}")
        
        # Aplicar estilo al área de entrada
        self.input_text.setStyleSheet(f"""
            QTextEdit {{ 
                background-color: {styles['input_bg']}; 
                color: {styles['text_color']}; 
                border: 2px solid {styles['input_border']}; 
                border-radius: 5px; 
                padding: 5px; 
            }}
        """)
        
        # Aplicar estilo al botón de enviar
        self.send_button.setStyleSheet(f"""
            QPushButton {{ 
                background-color: {styles['button_bg']}; 
                color: white; 
                border: none; 
                border-radius: 5px; 
                padding: 8px; 
                font-weight: bold; 
            }} 
            QPushButton:hover {{ 
                background-color: {styles['button_hover']}; 
            }}
        """)
        
        # Aplicar estilo a la etiqueta de estado
        self.status_label.setStyleSheet(f"QLabel {{ color: {styles['status_color']}; padding: 5px; }}")
        
        # Recargar todos los mensajes con el nuevo tema
        self.reload_messages_with_theme(styles)
    
    def reload_messages_with_theme(self, styles):
        """Recarga todos los mensajes aplicando el nuevo tema"""
        # Limpiar el chat actual
        for i in reversed(range(self.chat_layout.count())):
            child = self.chat_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Recargar todos los mensajes del historial
        for msg in self.history:
            self.append_chat_with_theme(msg["author"], msg["text"], styles, 
                                      add_to_history=False, fecha_hora=msg.get("fecha_hora"))
    
    def append_chat_with_theme(self, author, text, styles, add_to_history=True, fecha_hora=None):
        """Versión de append_chat que usa estilos específicos"""
        max_length = 4096
        display_text = text[:max_length] + ("..." if len(text) > max_length else "")
        
        if fecha_hora is None:
            fecha_hora = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        
        # Widget del mensaje
        message_widget = QWidget()
        message_layout = QVBoxLayout(message_widget)
        
        # Header con autor, fecha y botón copiar
        header_layout = QHBoxLayout()
        
        author_label = QLabel(author)
        author_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        if author == "Tú":
            author_label.setStyleSheet("background-color: #2c5aa0; color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold;")
        elif author in ["DeepSeek", "ChatGPT"]:
            author_label.setStyleSheet("background-color: #c7254e; color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold;")
        else:
            author_label.setStyleSheet("background-color: #666666; color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold;")
        header_layout.addWidget(author_label)
        
        fecha_label = QLabel(fecha_hora)
        fecha_label.setFont(QFont("Segoe UI", 8))
        fecha_label.setStyleSheet(f"background-color: {styles['date_bg']}; color: {styles['date_color']}; padding: 2px 6px; border-radius: 3px;")
        header_layout.addWidget(fecha_label)
        
        # Agregar botón de copiar para todos los mensajes
        copy_button = QPushButton("📋 Copiar")
        copy_button.setStyleSheet(f"QPushButton {{ background-color: {styles['copy_button_bg']}; color: white; border: none; border-radius: 3px; padding: 4px 8px; }} QPushButton:hover {{ background-color: {styles['copy_button_hover']}; }}")
        copy_button.clicked.connect(lambda: self.copy_message(text))
        header_layout.addWidget(copy_button)
        
        if author in ["DeepSeek", "ChatGPT"]:
            self.replies.append(text)
        
        header_layout.addStretch()
        message_layout.addLayout(header_layout)
        
        # Contenido del mensaje
        text_label = QLabel(display_text)
        text_label.setWordWrap(True)
        text_label.setFont(QFont("Segoe UI", 10))
        if author in ["DeepSeek", "ChatGPT"]:
            text_label.setStyleSheet(f"background-color: {styles['bot_msg_bg']}; color: {styles['bot_msg_color']}; padding: 10px; border-radius: 8px; border-left: 4px solid {styles['bot_msg_border']};")
        else:
            text_label.setStyleSheet(f"background-color: {styles['user_msg_bg']}; color: {styles['user_msg_color']}; padding: 10px; border-radius: 8px;")
        text_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        message_layout.addWidget(text_label)
        
        self.chat_layout.addWidget(message_widget)
        
        # Scroll automático al final
        QTimer.singleShot(10, self.scroll_to_bottom)
        
        if add_to_history:
            self.history.append({"author": author, "text": text, "fecha_hora": fecha_hora})
        
        # Renombrar archivo y pestaña cuando el usuario hace una pregunta
        if author == "Tú" and self.parent_tabs is not None:
            self.rename_chat_from_message(text)
    
    def append_chat(self, author, text, add_to_history=True, fecha_hora=None):
            self.history = []
    
    def save_history(self):
        """Guarda historial en archivo JSON."""
        try:
            with open(self.historial_path, "w", encoding="utf-8") as f:
                json.dump({"titulo": self.titulo, "mensajes": self.history}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Historial", f"No se pudo guardar el historial: {e}")
    
    def append_chat(self, author, text, add_to_history=True, fecha_hora=None):
        """Añade un mensaje al chat usando el tema actual."""
        # Obtener estilos del tema actual desde la ventana principal
        if hasattr(self.parent(), 'is_dark_mode'):
            is_dark = self.parent().is_dark_mode
            styles = self.parent().get_dark_theme_styles() if is_dark else self.parent().get_light_theme_styles()
        else:
            # Fallback a tema oscuro si no se puede determinar
            styles = {
                "main_bg": "#1e1e1e", "chat_bg": "#1e1e1e", "input_bg": "#2d2d2d",
                "input_border": "#555555", "text_color": "white", "bot_msg_bg": "#2d2d2d",
                "bot_msg_color": "#e6e6e6", "bot_msg_border": "#c7254e", "user_msg_bg": "#0d47a1",
                "user_msg_color": "white", "button_bg": "#0d7377", "button_hover": "#14a085",
                "copy_button_bg": "#555555", "copy_button_hover": "#777777", "date_bg": "#404040",
                "date_color": "#cccccc", "status_color": "#cccccc"
            }
        
        self.append_chat_with_theme(author, text, styles, add_to_history, fecha_hora)
    
    def rename_chat_from_message(self, text):
        """Renombra el chat basado en el primer mensaje del usuario."""
        # Solo renombrar si aún no se ha renombrado y si es un archivo "Chat_nuevo_"
        if self.renombrado or not os.path.basename(self.historial_path).startswith("Chat_nuevo_"):
            return
            
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
        
        # Guardar el historial actual antes de renombrar
        self.save_history()
        
        try:
            # Usar shutil.move en lugar de os.rename para mejor compatibilidad
            import shutil
            shutil.move(self.historial_path, nuevo_json)
            self.historial_path = nuevo_json
            self.renombrado = True
        except Exception as e:
            # Si falla el renombrado, no es crítico - el chat sigue funcionando
            print(f"No se pudo renombrar el historial: {e}")
            self.renombrado = True  # Marcar como renombrado para evitar intentos futuros
        
        # Actualiza el título y la pestaña
        self.titulo = texto_original
        for i in range(self.parent_tabs.count()):
            if self.parent_tabs.widget(i) == self:
                self.parent_tabs.setTabText(i, texto_original)
                break
                break
    
    def start_reply(self, author):
        """Inicia una respuesta en streaming."""
        self._in_streaming = True
        self.last_reply = ""
        
        fecha_hora = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        
        # Widget para la respuesta
        self.reply_widget = QWidget()
        reply_layout = QVBoxLayout(self.reply_widget)
        
        # Header
        header_layout = QHBoxLayout()
        
        author_label = QLabel(author)
        author_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        if author == "Tú":
            author_label.setStyleSheet("background-color: #2c5aa0; color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold;")
        elif author in ["DeepSeek", "ChatGPT"]:
            author_label.setStyleSheet("background-color: #c7254e; color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold;")
        else:
            author_label.setStyleSheet("background-color: #666666; color: white; padding: 4px 8px; border-radius: 3px; font-weight: bold;")
        header_layout.addWidget(author_label)
        
        fecha_label = QLabel(fecha_hora)
        fecha_label.setFont(QFont("Segoe UI", 8))
        fecha_label.setStyleSheet("background-color: #404040; color: #cccccc; padding: 2px 6px; border-radius: 3px;")
        header_layout.addWidget(fecha_label)
        
        self.reply_copy_button = QPushButton("📋 Copiar")
        self.reply_copy_button.setStyleSheet("QPushButton { background-color: #555555; color: white; border: none; border-radius: 3px; padding: 4px 8px; } QPushButton:hover { background-color: #777777; }")
        self.reply_copy_button.clicked.connect(lambda: self.copy_message(self.last_reply))
        header_layout.addWidget(self.reply_copy_button)
        
        header_layout.addStretch()
        reply_layout.addLayout(header_layout)
        
        # Contenido de la respuesta
        self.reply_label = QLabel("● ● ● escribiendo...")
        self.reply_label.setWordWrap(True)
        self.reply_label.setFont(QFont("Segoe UI", 10))
        self.reply_label.setStyleSheet("background-color: #2d2d2d; color: #e6e6e6; padding: 10px; border-radius: 8px; border-left: 4px solid #c7254e;")
        self.reply_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        reply_layout.addWidget(self.reply_label)
        
        self.chat_layout.addWidget(self.reply_widget)
        QTimer.singleShot(10, self.scroll_to_bottom)
        
        # Crear timer para animar el indicador de escritura
        self.typing_timer = QTimer()
        self.typing_timer.timeout.connect(self.animate_typing_indicator)
        self.typing_dots = 0
        self.typing_timer.start(500)  # Cambiar cada 500ms
    
    def update_reply(self, text):
        """Actualiza el texto de la respuesta en streaming con efectos visuales."""
        max_length = 4096
        if self._in_streaming and self.reply_label:
            # Detener la animación de typing cuando llega el primer texto
            if hasattr(self, 'typing_timer') and self.typing_timer.isActive():
                self.typing_timer.stop()
            
            current = self.reply_label.text()
            # Si es el primer texto y aún muestra el indicador, limpiar
            if "escribiendo..." in current:
                current = ""
                
            new_text = (current + text)[:max_length]
            
            # Agregar cursor parpadeante al final para simular escritura
            display_text = new_text + "▌"
            if len(current + text) > max_length:
                display_text += "..."
                
            self.reply_label.setText(display_text)
            self.last_reply = new_text
            
            # Auto-scroll más frecuente durante streaming para seguir el texto
            QTimer.singleShot(5, self.scroll_to_bottom)
            
            # Actualizar el widget para forzar repintado
            self.reply_label.update()
    
    def animate_typing_indicator(self):
        """Anima el indicador de escritura antes de que llegue el primer texto."""
        if self._in_streaming and self.reply_label and self.last_reply == "":
            dots = ["●", "● ●", "● ● ●"]
            self.typing_dots = (self.typing_dots + 1) % len(dots)
            self.reply_label.setText(f"{dots[self.typing_dots]} escribiendo...")
    
    def end_reply(self):
        """Finaliza la respuesta en streaming."""
        if self._in_streaming:
            self._in_streaming = False
            # Detener timer de animación si está activo
            if hasattr(self, 'typing_timer') and self.typing_timer.isActive():
                self.typing_timer.stop()
            # Quitar el cursor parpadeante y mostrar texto final
            if self.reply_label:
                self.reply_label.setText(self.last_reply)
            self.replies.append(self.last_reply)
            fecha_hora = datetime.now().strftime("%d/%m/%y %H:%M:%S")
            self.history.append({"author": self.ia_tipo, "text": self.last_reply, "fecha_hora": fecha_hora})
            # Scroll final
            QTimer.singleShot(100, self.scroll_to_bottom)
    
    def scroll_to_bottom(self):
        """Hace scroll hasta abajo del chat de forma suave."""
        scrollbar = self.scroll_area.verticalScrollBar()
        current_value = scrollbar.value()
        max_value = scrollbar.maximum()
        
        # Solo hacer scroll si no estamos ya en el fondo (optimización)
        if current_value < max_value - 10:  # Pequeño margen para evitar scroll innecesario
            # Scroll suave: si la diferencia es grande, hacer scroll animado
            diff = max_value - current_value
            if diff > 100:
                # Para diferencias grandes, usar scroll gradual
                self.smooth_scroll_to_bottom(current_value, max_value)
            else:
                # Para diferencias pequeñas, scroll directo
                scrollbar.setValue(max_value)
    
    def smooth_scroll_to_bottom(self, start_value, end_value):
        """Realiza un scroll suave al final."""
        scrollbar = self.scroll_area.verticalScrollBar()
        steps = 5
        step_size = (end_value - start_value) // steps
        
        def scroll_step(step):
            if step <= steps:
                new_value = start_value + (step_size * step)
                if step == steps:
                    new_value = end_value  # Asegurar que llegue al final
                scrollbar.setValue(new_value)
                if step < steps:
                    QTimer.singleShot(20, lambda: scroll_step(step + 1))
        
        scroll_step(1)
    
    def on_send(self):
        """Envía el mensaje del usuario y inicia el hilo para obtener la respuesta."""
        user_text = self.input_text.toPlainText().strip()
        if not user_text:
            return
        
        self.input_text.clear()
        self.append_chat("Tú", user_text)
        
        # Inicia el hilo de streaming
        self.status_label.setText("Respondiendo...")
        self.start_reply("DeepSeek" if self.ia_tipo == "Deepseek" else self.ia_tipo)
        
        self.stream_thread = ChatStreamThread(self.bot, user_text, self.ia_tipo, self.api_keys)
        self.stream_thread.chunk_received.connect(self.update_reply)
        self.stream_thread.finished_streaming.connect(self.on_reply_finished)
        self.stream_thread.error_occurred.connect(self.on_reply_error)
        self.stream_thread.start()
    
    def on_reply_finished(self, full_reply):
        """Maneja la finalización de la respuesta."""
        self.last_reply = full_reply
        self.end_reply()
        self.status_label.setText("Listo.")
    
    def on_reply_error(self, error_msg):
        """Maneja errores en la respuesta."""
        self.append_chat("Error", error_msg)
        self.status_label.setText("Error en la petición.")
        self._in_streaming = False
    
    def on_text_changed(self):
        """Se ejecuta cuando el usuario cambia el texto en el área de entrada."""
        # Auto-scroll suave al final del chat cuando el usuario escribe
        QTimer.singleShot(50, self.scroll_to_bottom)
    
    def on_cursor_moved(self):
        """Se ejecuta cuando el cursor se mueve en el área de entrada."""
        # Auto-scroll más sutil cuando solo se mueve el cursor
        QTimer.singleShot(100, self.scroll_to_bottom)
    
    def copy_message(self, text):
        """Copia el mensaje al portapapeles."""
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copiado", "Mensaje copiado al portapapeles ✅")
        else:
            QMessageBox.warning(self, "Aviso", "No hay ningún mensaje para copiar.")
    
    def closeEvent(self, event):
        """Guarda el historial al cerrar."""
        self.save_history()
        event.accept()

class UpdateKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Actualizar Key")
        self.setFixedSize(300, 160)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Seleccione la IA:"))
        
        self.ia_combo = QComboBox()
        self.ia_combo.addItems(["Deepseek", "ChatGPT"])
        layout.addWidget(self.ia_combo)
        
        layout.addWidget(QLabel("Nueva API Key:"))
        
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_values(self):
        return self.ia_combo.currentText(), self.key_input.text()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.chat_widgets = []
        self.conversaciones_dir = None
        self.ia_tipo = None
        self.api_keys = None
        self.bot = None
        
        self.setWindowTitle("DeepSeek Chat (Streaming) - PyQt")
        self.setGeometry(100, 100, 1000, 700)
        
        # Cargar tema desde configuración
        self.is_dark_mode = self.load_theme_preference()
        
        self.init_ui()
        self.init_data()
    
    def load_theme_preference(self):
        """Carga la preferencia de tema desde settings.json"""
        settings = get_settings()
        return settings.get("dark_mode", True)  # Modo oscuro por defecto
    
    def save_theme_preference(self, is_dark):
        """Guarda la preferencia de tema en settings.json"""
        settings = get_settings()
        settings["dark_mode"] = is_dark
        save_settings(settings)
    
    def get_dark_theme_styles(self):
        """Retorna los estilos para el tema oscuro"""
        return {
            "main_bg": "#1e1e1e",
            "chat_bg": "#1e1e1e", 
            "input_bg": "#2d2d2d",
            "input_border": "#555555",
            "text_color": "white",
            "bot_msg_bg": "#2d2d2d",
            "bot_msg_color": "#e6e6e6",
            "bot_msg_border": "#c7254e",
            "user_msg_bg": "#0d47a1",
            "user_msg_color": "white",
            "button_bg": "#0d7377",
            "button_hover": "#14a085",
            "copy_button_bg": "#555555",
            "copy_button_hover": "#777777",
            "date_bg": "#404040",
            "date_color": "#cccccc",
            "status_color": "#cccccc"
        }
    
    def get_light_theme_styles(self):
        """Retorna los estilos para el tema claro"""
        return {
            "main_bg": "#ffffff",
            "chat_bg": "#ffffff",
            "input_bg": "#ffffff", 
            "input_border": "#cccccc",
            "text_color": "#333333",
            "bot_msg_bg": "#f8f9fa",
            "bot_msg_color": "#333333",
            "bot_msg_border": "#dc3545",
            "user_msg_bg": "#007bff",
            "user_msg_color": "white",
            "button_bg": "#28a745",
            "button_hover": "#218838",
            "copy_button_bg": "#6c757d",
            "copy_button_hover": "#545b62",
            "date_bg": "#e9ecef",
            "date_color": "#6c757d",
            "status_color": "#6c757d"
        }
    
    def toggle_theme(self, checked):
        """Cambia entre tema oscuro y claro"""
        self.is_dark_mode = checked
        self.save_theme_preference(checked)
        
        # Actualizar texto del toggle
        if checked:
            self.theme_toggle.setText("🌙 Modo Oscuro")
        else:
            self.theme_toggle.setText("☀️ Modo Claro")
        
        # Aplicar tema a toda la aplicación
        self.apply_theme_to_all()
    
    def apply_theme_to_all(self):
        """Aplica el tema actual a toda la interfaz"""
        styles = self.get_dark_theme_styles() if self.is_dark_mode else self.get_light_theme_styles()
        
        # Aplicar estilo a la ventana principal
        self.setStyleSheet(f"QMainWindow {{ background-color: {styles['main_bg']}; color: {styles['text_color']}; }}")
        
        # Aplicar tema a todas las pestañas de chat
        for i in range(self.tabs.count()):
            chat_widget = self.tabs.widget(i)
            if hasattr(chat_widget, 'apply_theme'):
                chat_widget.apply_theme(styles)
    
    def init_ui(self):
        # Widget central con pestañas
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Menú
        self.create_menu()
        
        # Botones para nuevas pestañas
        self.create_tab_buttons()
        
        # Aplicar tema inicial
        self.apply_theme_to_all()
    
    def create_menu(self):
        menubar = self.menuBar()
        
        # Menú Usuario
        usuario_menu = menubar.addMenu("Usuario")
        usuario_menu.addAction("Perfil de usuario", lambda: QMessageBox.information(self, "Usuario", "Función de perfil de usuario"))
        
        # Menú IA
        ia_menu = menubar.addMenu("IA Prompt")
        ia_menu.addAction("Deepseek", lambda: self.seleccionar_ia_desde_menu("Deepseek"))
        ia_menu.addAction("ChatGPT", lambda: self.seleccionar_ia_desde_menu("ChatGPT"))
        
        # Menú Ajustes
        ajustes_menu = menubar.addMenu("Ajustes")
        ajustes_menu.addAction("Actualizar Key", self.actualizar_key)
        ajustes_menu.addAction("Configuración", lambda: QMessageBox.information(self, "Ajustes", "Función de configuración"))
    
    def create_tab_buttons(self):
        # Toolbar con botones para pestañas
        toolbar = self.addToolBar("Tabs")
        toolbar.addAction("➕ Nuevo chat", self.crear_nuevo_chat)
        toolbar.addAction("✖ Cerrar pestaña", self.cerrar_pestana_actual)
        
        # Separador
        toolbar.addSeparator()
        
        # Toggle para modo oscuro/claro
        self.theme_toggle = QCheckBox("🌙 Modo Oscuro" if self.is_dark_mode else "☀️ Modo Claro")
        self.theme_toggle.setChecked(self.is_dark_mode)
        self.theme_toggle.toggled.connect(self.toggle_theme)
        self.theme_toggle.setStyleSheet("""
            QCheckBox {
                color: white;
                font-weight: bold;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #555555;
                border: 2px solid #777777;
                border-radius: 10px;
            }
            QCheckBox::indicator:checked {
                background-color: #0d7377;
                border: 2px solid #14a085;
                border-radius: 10px;
            }
        """)
        toolbar.addWidget(self.theme_toggle)
    
    def init_data(self):
        """Inicializa los datos necesarios para la aplicación."""
        self.ia_tipo, self.api_keys = get_api_key_and_ia()
        api_key = self.api_keys.get(self.ia_tipo)
        if not api_key:
            QMessageBox.critical(self, "Error", "No se ingresó una API Key.")
            return
        
        self.bot = self.crear_bot(self.ia_tipo, self.api_keys)
        
        self.conversaciones_dir = get_conversaciones_dir()
        if not self.conversaciones_dir:
            QMessageBox.critical(self, "Error", "No se seleccionó ninguna carpeta para conversaciones.")
            return
        
        self.load_existing_chats()
    
    def crear_bot(self, ia, api_keys):
        """Crea un bot según el tipo de IA."""
        if ia == "Deepseek":
            base_url = "https://api.deepseek.com"
            model = "deepseek-chat"
            return DeepSeekChat(api_keys["Deepseek"], base_url, model)
        elif ia == "ChatGPT":
            # No se usa DeepSeekChat, solo se pasa la key
            return None
        else:
            base_url = "https://api.deepseek.com"
            model = "deepseek-chat"
            return DeepSeekChat(api_keys["Deepseek"], base_url, model)
    
    def load_existing_chats(self):
        """Carga los chats existentes como pestañas."""
        archivos = [f for f in os.listdir(self.conversaciones_dir) if f.endswith(".json")]
        if not archivos:
            # Si no hay archivos, crea uno por defecto
            self.crear_archivo_chat_por_defecto()
            archivos = [f for f in os.listdir(self.conversaciones_dir) if f.endswith(".json")]
        
        for archivo in archivos:
            historial_path = os.path.join(self.conversaciones_dir, archivo)
            chat_widget = ChatWidget(self.bot, historial_path, self.tabs, self.ia_tipo, self.api_keys, self)
            
            tab_text = chat_widget.titulo if chat_widget.titulo else archivo.replace(".json", "")
            self.tabs.addTab(chat_widget, tab_text)
            self.chat_widgets.append(chat_widget)
    
    def crear_archivo_chat_por_defecto(self):
        """Crea un archivo de chat por defecto."""
        idx = 1
        while True:
            nuevo_nombre = f"Chat_nuevo_{idx}.json"
            historial_path = os.path.join(self.conversaciones_dir, nuevo_nombre)
            if not os.path.exists(historial_path):
                with open(historial_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                break
            idx += 1
    
    def crear_nuevo_chat(self):
        """Crea una nueva pestaña de chat."""
        idx = 1
        while True:
            nuevo_nombre = f"Chat_nuevo_{idx}.json"
            historial_path = os.path.join(self.conversaciones_dir, nuevo_nombre)
            if not os.path.exists(historial_path):
                with open(historial_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                break
            idx += 1
        
        # Usa la IA y key actual
        current_settings = get_settings()
        ia_actual = current_settings.get("ia_seleccionada", "Deepseek")
        api_keys_actual = current_settings.get("api_keys", {})
        bot_actual = self.crear_bot(ia_actual, api_keys_actual)
        
        chat_widget = ChatWidget(bot_actual, historial_path, self.tabs, ia_actual, api_keys_actual, self)
        tab_text = "Chat nuevo"
        
        tab_index = self.tabs.addTab(chat_widget, tab_text)
        self.chat_widgets.append(chat_widget)
        self.tabs.setCurrentIndex(tab_index)
    
    def cerrar_pestana_actual(self):
        """Cierra la pestaña actual."""
        current_index = self.tabs.currentIndex()
        if current_index >= 0:
            self.cerrar_pestana(current_index)
    
    def cerrar_pestana(self, index):
        """Cierra una pestaña específica."""
        if 0 <= index < len(self.chat_widgets):
            chat_widget = self.chat_widgets[index]
            chat_widget.save_history()
            
            try:
                if os.path.exists(chat_widget.historial_path):
                    os.remove(chat_widget.historial_path)
            except Exception as e:
                QMessageBox.warning(self, "Eliminar historial", f"No se pudo eliminar el historial: {e}")
            
            self.tabs.removeTab(index)
            del self.chat_widgets[index]
    
    def seleccionar_ia_desde_menu(self, ia_seleccionada):
        """Cambia la IA desde el menú."""
        settings = get_settings()
        api_keys = settings.get("api_keys", {})
        key = api_keys.get(ia_seleccionada)
        
        if not key:
            key, ok = QInputDialog.getText(self, "API Key", f"Ingrese la API Key para {ia_seleccionada}:", QLineEdit.EchoMode.Password)
            if not ok or not key:
                return
            
            if "api_keys" not in settings:
                settings["api_keys"] = {}
            settings["api_keys"][ia_seleccionada] = key
            save_settings(settings)
        
        settings["ia_seleccionada"] = ia_seleccionada
        save_settings(settings)
        
        # Actualiza todos los chats
        for chat_widget in self.chat_widgets:
            chat_widget.ia_tipo = ia_seleccionada
            chat_widget.api_keys = settings["api_keys"]
            if ia_seleccionada == "Deepseek":
                chat_widget.bot = self.crear_bot("Deepseek", settings["api_keys"])
            else:
                chat_widget.bot = None
        
        QMessageBox.information(self, "IA", f"IA seleccionada: {ia_seleccionada}\nKey guardada.")
    
    def actualizar_key(self):
        """Actualiza la API key de una IA."""
        dialog = UpdateKeyDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            ia_sel, nueva_key = dialog.get_values()
            
            settings = get_settings()
            if "api_keys" not in settings:
                settings["api_keys"] = {}
            settings["api_keys"][ia_sel] = nueva_key
            save_settings(settings)
            
            # Actualiza todos los chats
            for chat_widget in self.chat_widgets:
                chat_widget.api_keys = settings["api_keys"]
                if chat_widget.ia_tipo == ia_sel and ia_sel == "Deepseek":
                    chat_widget.bot = self.crear_bot("Deepseek", settings["api_keys"])
            
            QMessageBox.information(self, "Configuración", f"Key de {ia_sel} actualizada.")
    
    def closeEvent(self, event):
        """Guarda todos los historiales al cerrar la aplicación."""
        for chat_widget in self.chat_widgets:
            chat_widget.save_history()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Aplica un estilo más moderno
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()