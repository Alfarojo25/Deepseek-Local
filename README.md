\# DeepSeek Chat (Streaming)



Este es mi \*\*primer proyecto en Python\*\*, un cliente de chat gráfico que permite interactuar con la API de \*\*DeepSeek\*\* en tiempo real mediante \*\*streaming de respuestas\*\*.



La aplicación está desarrollada con \*\*Tkinter\*\* e implementa un sistema de pestañas para manejar múltiples conversaciones, cada una con su propio historial guardado en archivos `.json`.



\### 🚀 Características principales



\* Interfaz gráfica sencilla con \*\*Tkinter\*\*.

\* Soporte para múltiples chats en \*\*pestañas dinámicas\*\*.

\* Guardado y carga de conversaciones en archivos JSON.

\* Respuestas en \*\*tiempo real (streaming)\*\* desde la API de DeepSeek.

\* Sistema de copia rápida de mensajes.

\* Renombrado automático de archivos y pestañas según el contenido del chat.

\* Configuración persistente mediante `settings.json` (API Key y carpeta de conversaciones).



\### 📂 Organización del código



\* `DeepSeekChat`: clase que gestiona la conexión con la API de DeepSeek.

\* `ChatApp`: interfaz de usuario para cada pestaña de chat.

\* `get\_api\_key()` y `get\_conversaciones\_dir()`: gestión de credenciales y directorio de historial.

\* `main()`: inicializa la aplicación y crea la ventana principal con pestañas.



\### 🛠️ Requisitos



\* Python 3.8+

\* Dependencias:



&nbsp; ```bash

&nbsp; pip install openai

&nbsp; ```



&nbsp; (además de las librerías estándar incluidas en Python: `tkinter`, `json`, `os`, etc.)



\### 📜 Licencia



Este proyecto está bajo la licencia \*\*GNU General Public License v3.0 (GPL-3.0)\*\*.

Puedes usarlo, modificarlo y distribuirlo bajo los términos de esta licencia.



