# DeepSeek Chat - Cliente de IA con Interfaz Gráfica

## Descripción

DeepSeek Chat es una aplicación de escritorio desarrollada en Python que proporciona una interfaz gráfica moderna para interactuar con modelos de inteligencia artificial. La aplicación soporta tanto DeepSeek como ChatGPT, ofreciendo una experiencia de chat fluida con respuestas en tiempo real mediante streaming.

La aplicación está construida con PyQt6 y presenta un diseño profesional con soporte para múltiples conversaciones, temas personalizables y una amplia gama de funcionalidades avanzadas.

## Características Principales

### Interfaz de Usuario
- **Interfaz gráfica moderna** desarrollada con PyQt6
- **Sistema de pestañas dinámicas** para manejar múltiples conversaciones simultáneamente
- **Tema dual** con modo claro y oscuro (oscuro por defecto)
- **Toggle de tema** en la barra de herramientas para cambio instantáneo
- **Barra de menús** con opciones organizadas por categorías
- **Área de chat optimizada** con scroll automático inteligente

### Funcionalidades de Chat
- **Respuestas en tiempo real** mediante streaming de la API
- **Indicador visual de escritura** con animación de puntos antes de la respuesta
- **Cursor parpadeante** durante el streaming para simular escritura en vivo
- **Auto-scroll inteligente** que sigue el texto mientras se escribe
- **Botón de copia** disponible para todos los mensajes (usuario e IA)
- **Límite de caracteres** con truncado inteligente para mensajes largos
- **Formato de fecha unificado** (DD/MM/AA HH:MM:SS) para todos los mensajes

### Gestión de Conversaciones
- **Guardado automático** de conversaciones en formato JSON con codificación UTF-8
- **Carga automática** del historial al reabrir la aplicación
- **Renombrado inteligente** de archivos basado en el primer mensaje del usuario
- **Soporte completo para caracteres especiales** (tildes, ñ, etc.)
- **Estructura de datos mejorada** con metadatos de título y fecha

### Soporte Multi-IA
- **DeepSeek** como modelo principal
- **ChatGPT** como modelo alternativo
- **Gestión centralizada de API Keys** con almacenamiento seguro
- **Selección de IA** desde el menú principal
- **Configuración independiente** para cada modelo

### Configuración y Persistencia
- **Archivo de configuración** (settings.json) para preferencias del usuario
- **Selección de directorio** personalizable para almacenar conversaciones
- **Persistencia de tema** seleccionado entre sesiones
- **Gestión automática de dependencias** con instalación bajo demanda
- **Configuración de API Keys** con interfaz gráfica

## Arquitectura del Sistema

### Estructura de Clases

#### DeepSeekChat
Clase principal para la gestión de la API de DeepSeek:
- Manejo de conexiones HTTP con streaming
- Gestión del historial de mensajes
- Procesamiento de respuestas en tiempo real

#### ChatStreamThread
Hilo de trabajo para el procesamiento asíncrono:
- Ejecución no bloqueante de peticiones API
- Emisión de señales para actualización de UI
- Manejo de errores y timeouts

#### ChatWidget
Widget principal para cada pestaña de chat:
- Gestión de la interfaz de usuario del chat
- Aplicación de temas y estilos
- Manejo de eventos de usuario
- Persistencia de datos

#### MainWindow
Ventana principal de la aplicación:
- Gestión del sistema de pestañas
- Menús y barra de herramientas
- Sistema de temas globales
- Coordinación entre componentes

### Sistema de Temas

#### Tema Oscuro (Predeterminado)
- Fondo principal: Negro profundo (#1e1e1e)
- Área de texto: Gris oscuro (#2d2d2d)
- Mensajes de IA: Gris medio con borde rojo
- Mensajes de usuario: Azul oscuro
- Botones: Verde azulado con efectos hover

#### Tema Claro
- Fondo principal: Blanco (#ffffff)
- Área de texto: Blanco con bordes grises
- Mensajes de IA: Gris claro con borde rojo
- Mensajes de usuario: Azul Bootstrap
- Botones: Verde Bootstrap con efectos hover

## Requisitos del Sistema

### Requisitos Mínimos
- **Sistema Operativo**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.8 o superior
- **Memoria RAM**: 512 MB mínimo (1 GB recomendado)
- **Espacio en disco**: 100 MB para la aplicación y dependencias

### Dependencias
```bash
pip install PyQt6 openai
```

Librerías estándar incluidas:
- `os`, `sys`, `json`, `threading`
- `datetime`, `shutil`

## Instalación y Configuración

### Instalación Automática
La aplicación incluye un sistema de instalación automática de dependencias que se ejecuta en el primer inicio.

### Configuración Manual
1. Clona o descarga el repositorio
2. Instala las dependencias:
   ```bash
   pip install PyQt6 openai
   ```
3. Ejecuta la aplicación:
   ```bash
   python Deepseek_local.py
   ```

### Primera Configuración
1. **API Key**: La aplicación solicitará tu clave API de DeepSeek/ChatGPT
2. **Directorio de conversaciones**: Selecciona la carpeta donde guardar los chats
3. **Preferencias**: Configura el tema y otros ajustes desde el menú

## Uso de la Aplicación

### Inicio de una Conversación
1. Ejecuta la aplicación
2. Se abrirá automáticamente una nueva pestaña de chat
3. Escribe tu mensaje en el área de texto inferior
4. Presiona "Enviar" o Enter para enviar el mensaje

### Gestión de Pestañas
- **Nuevo chat**: Botón "+" en la barra de herramientas
- **Cerrar pestaña**: Botón "X" en la barra de herramientas
- **Cambio de pestaña**: Click en las pestañas superiores

### Cambio de Tema
- Utiliza el toggle "Modo Oscuro/Claro" en la barra de herramientas
- El cambio se aplica inmediatamente a toda la interfaz
- La preferencia se guarda automáticamente

### Configuración Avanzada
- **Menú IA Prompt**: Cambiar entre DeepSeek y ChatGPT
- **Menú Ajustes**: Actualizar API Keys y configuraciones
- **Menú Usuario**: Opciones de perfil (en desarrollo)

## Estructura de Archivos

```
DeepSeek-Chat/
├── Deepseek_local.py          # Archivo principal de la aplicación
├── settings.json              # Configuraciones del usuario
├── conversaciones/            # Directorio de conversaciones
│   ├── chat_1.json           # Archivos individuales de chat
│   ├── chat_2.json
│   └── ...
├── README.md                  # Este archivo
└── LICENSE                    # Licencia GPL-3.0
```

### Formato de Conversaciones
```json
{
  "titulo": "Nombre del chat",
  "mensajes": [
    {
      "author": "Tú",
      "text": "Mensaje del usuario",
      "fecha_hora": "20/09/25 14:30:25"
    },
    {
      "author": "DeepSeek",
      "text": "Respuesta de la IA",
      "fecha_hora": "20/09/25 14:30:27"
    }
  ]
}
```

## Características Técnicas

### Optimizaciones de Rendimiento
- **Scroll inteligente**: Solo se activa cuando es necesario
- **Streaming optimizado**: Procesamiento en hilos separados
- **Gestión de memoria**: Limpieza automática de widgets no utilizados
- **Carga bajo demanda**: Los chats se cargan solo cuando se seleccionan

### Características de Seguridad
- **Almacenamiento seguro** de API Keys
- **Validación de entrada** para prevenir inyecciones
- **Manejo de errores** robusto con recuperación automática
- **Codificación UTF-8** completa para soporte internacional

### Compatibilidad
- **Multiplataforma**: Windows, macOS, Linux
- **Resoluciones**: Adaptable a diferentes tamaños de pantalla
- **Teclados**: Soporte para atajos de teclado
- **Accesibilidad**: Controles accesibles con navegación por teclado

## Solución de Problemas

### Problemas Comunes

#### Error de API Key
- Verifica que la API Key sea válida
- Revisa los límites de tu cuenta API
- Actualiza la clave desde el menú Ajustes

#### Problemas de Conexión
- Verifica tu conexión a internet
- Revisa la configuración de proxy si aplica
- Reinicia la aplicación

#### Errores de Archivo
- Verifica permisos de escritura en el directorio de conversaciones
- Asegúrate de que el disco tenga espacio suficiente
- Revisa que no haya archivos corruptos en la carpeta

### Logs de Depuración
La aplicación genera logs en la consola para facilitar la depuración de problemas.

## Contribuciones

Este proyecto está abierto a contribuciones. Para contribuir:

1. Fork el repositorio
2. Crea una rama para tu feature: `git checkout -b nueva-caracteristica`
3. Commit tus cambios: `git commit -am 'Agregar nueva característica'`
4. Push a la rama: `git push origin nueva-caracteristica`
5. Crea un Pull Request

### Áreas de Mejora
- Soporte para más modelos de IA
- Exportación de conversaciones a PDF
- Sistema de plugins
- Interfaz de configuración avanzada
- Soporte para imágenes y archivos

## Licencia

Este proyecto está licenciado bajo la GNU General Public License v3.0 (GPL-3.0).

Puedes usar, modificar y distribuir este software bajo los términos de esta licencia. Para más detalles, consulta el archivo [LICENSE](LICENSE).

## Contacto y Soporte

Para reportar problemas, sugerir mejoras o hacer preguntas:

- **Issues**: Usa el sistema de issues de GitHub
- **Documentación**: Consulta este README para información detallada
- **Licencia**: GPL-3.0 para uso libre y modificación

---

**Versión**: 2.0.0  
**Última actualización**: Septiembre 2025  
**Compatibilidad**: Python 3.8+ | PyQt6 | Windows/macOS/Linux