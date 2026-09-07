# 🏗️ Guía de Desarrollo MCP - Estándar para Creación de Servidores MCP 100% Puros

## 📋 Propósito de esta Guía

Esta guía sirve como **estándar definitivo** para crear servidores MCP (Model Context Protocol) 100% puros y funcionales. Cualquier LLM puede usar este documento para crear un servidor MCP completo desde cero.

---

## 🎯 Principios Fundamentales de MCP

### ✅ **QUÉ ES MCP:**
- **Protocolo stdio** - Comunicación vía stdin/stdout
- **Herramientas estructuradas** - Funciones que Claude puede llamar
- **Recursos opcionales** - Información adicional que puede leer
- **JSON-RPC 2.0** - Protocolo de mensajes subyacente
- **Asíncrono** - Todas las operaciones son async/await

### ❌ **QUÉ NO ES MCP:**
- **NO es HTTP/REST** - No necesita FastAPI, Express, etc.
- **NO usa Docker** - Se ejecuta localmente
- **NO es una API web** - No tiene endpoints HTTP
- **NO necesita servidor web** - Solo Python ejecutándose

---

## 🛠️ Estructura de Proyecto MCP Estándar

```
mi_mcp_server/
├── 🚀 mcp_server.py          # Servidor MCP principal (OBLIGATORIO)
├── 📄 claude-config.json     # Configuración Claude Code (OBLIGATORIO)
├── 📋 pyproject.toml        # Dependencias directas (OBLIGATORIO)
├── 🔒 uv.lock               # Resolución reproducible (OBLIGATORIO)
├── 🔧 services/              # Lógica de negocio
│   ├── __init__.py
│   └── core_service.py       # Tu servicio principal
├── 📊 models/                # Modelos de datos con Pydantic
│   ├── __init__.py
│   └── data_models.py        # Modelos de validación
├── ⚙️ config/                # Configuración
│   ├── __init__.py
│   └── settings.py           # Settings con variables de entorno
├── 🧪 tests/                 # Tests (RECOMENDADO)
│   ├── __init__.py
│   └── test_server.py        # Tests del servidor MCP
├── 🛠️ scripts/               # Scripts de utilidades
│   └── test-connection.py    # Test de conectividad
├── 📄 .env.example           # Configuración de ejemplo
└── 📖 README.md              # Documentación
```

---

## 📦 Dependencias Esenciales

### **pyproject.toml mínimo:**
```toml
[project]
name = "mi-mcp-server"
version = "1.0.0"
requires-python = ">=3.14,<3.15"
dependencies = [
    "mcp>=2,<3",
    "httpx>=0.25.2,<1",
    "pydantic>=2.12,<3",
]

[dependency-groups]
dev = ["pytest>=7.4.3", "black>=23.11", "isort>=5.12", "flake8>=6.1"]

[tool.uv]
package = false
```

### **Instalar dependencias:**
```bash
uv lock
uv sync --locked
```

---

## 🔧 Plantilla de Servidor MCP

### **mcp_server.py** (Archivo principal):
```python
#!/usr/bin/env python3
"""
Plantilla estándar para servidor MCP
Reemplaza [MI_SERVICIO] con el nombre de tu servicio
"""

import logging
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

# Importar tus servicios locales
from services.core_service import CoreService
from models.data_models import MiModelo
from config.settings import get_settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar servicios
settings = get_settings()
core_service = CoreService()

# MCPServer genera los esquemas desde los tipos y docstrings.
server = MCPServer(
    "[mi-servicio]-mcp",
    title="Mi servicio",
    description="Descripción del servidor",
    version="1.0.0",
)

@server.tool(
    title="Mi herramienta principal",
    annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True),
)
async def mi_herramienta_principal(
    parametro_requerido: Annotated[
        str,
        Field(min_length=1, description="Descripción del parámetro"),
    ],
    parametro_opcional: bool = False,
) -> dict[str, Any]:
    """Descripción clara de qué hace esta herramienta."""
    resultado = await core_service.procesar(parametro_requerido)
    return resultado.model_dump(mode="json")

@server.resource(
    "mi-servicio://info",
    name="informacion_servicio",
    mime_type="application/json",
)
def informacion_servicio() -> dict[str, Any]:
    """Expone las capacidades del servicio."""
    return {"version": "1.0.0", "capabilities": ["mi_herramienta_principal"]}

def main() -> None:
    """Ejecuta el servidor con el transporte stdio."""
    logger.info("🚀 Iniciando servidor MCP [MI_SERVICIO]...")
    server.run(transport="stdio")

if __name__ == "__main__":
    main()
```

---

## 📊 Plantilla de Modelos Pydantic

### **models/data_models.py**:
```python
"""
Modelos de datos para validación con Pydantic
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

class MiModelo(BaseModel):
    """Modelo principal de datos"""
    
    id: str = Field(..., description="Identificador único")
    nombre: str = Field(..., description="Nombre descriptivo")
    valor: Optional[float] = Field(None, description="Valor numérico opcional")
    activo: bool = Field(default=True, description="Estado activo")
    fecha_creacion: datetime = Field(default_factory=datetime.now)
    metadatos: Optional[Dict[str, Any]] = Field(None, description="Datos adicionales")
    
    @validator('id')
    def validar_id(cls, v):
        """Validar formato del ID"""
        if len(v) < 3:
            raise ValueError('ID debe tener al menos 3 caracteres')
        return v.upper()

class RespuestaServicio(BaseModel):
    """Respuesta estándar del servicio"""
    
    datos: Optional[MiModelo] = None
    estado: str = Field(default="exitoso")
    mensaje: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    datos_raw: Optional[Dict[str, Any]] = Field(None, description="Datos originales")

class ConfiguracionServicio(BaseModel):
    """Configuración del servicio"""
    
    timeout: int = Field(default=30, description="Timeout en segundos")
    reintentos: int = Field(default=3, description="Número de reintentos")
    debug: bool = Field(default=False, description="Modo debug")
```

---

## ⚙️ Plantilla de Configuración

### **config/settings.py**:
```python
"""
Configuración centralizada del servicio MCP
"""

import os
from typing import Optional

class Settings:
    """Configuración de la aplicación"""
    
    def __init__(self):
        # Configuración básica
        self.app_name = os.getenv("MI_SERVICIO_APP_NAME", "Mi Servicio MCP")
        self.app_version = os.getenv("MI_SERVICIO_APP_VERSION", "1.0.0")
        self.debug = os.getenv("MI_SERVICIO_DEBUG", "false").lower() == "true"
        
        # Configuración específica del servicio
        self.api_url = os.getenv("MI_SERVICIO_API_URL", "https://api.ejemplo.com")
        self.api_key = os.getenv("MI_SERVICIO_API_KEY")
        self.timeout = int(os.getenv("MI_SERVICIO_TIMEOUT", "30"))
        self.max_reintentos = int(os.getenv("MI_SERVICIO_MAX_REINTENTOS", "3"))
        
        # Logging
        self.log_level = os.getenv("MI_SERVICIO_LOG_LEVEL", "INFO")

def get_settings() -> Settings:
    """Obtiene la configuración de la aplicación"""
    return Settings()

# Mensajes de error estándar
ERROR_MESSAGES = {
    "PARAMETRO_INVALIDO": "El parámetro proporcionado no es válido",
    "SERVICIO_NO_DISPONIBLE": "El servicio externo no está disponible",
    "LIMITE_VELOCIDAD": "Se ha excedido el límite de consultas",
    "TIMEOUT": "La consulta ha excedido el tiempo límite",
    "API_KEY_INVALIDA": "La clave de API no es válida"
}
```

---

## 🔧 Plantilla de Servicio Principal

### **services/core_service.py**:
```python
"""
Servicio principal - aquí va tu lógica de negocio
"""

import asyncio
import logging
from typing import Optional
import httpx

from models.data_models import MiModelo, RespuestaServicio
from config.settings import get_settings, ERROR_MESSAGES

logger = logging.getLogger(__name__)

class CoreService:
    """Servicio principal con la lógica de negocio"""
    
    def __init__(self):
        self.settings = get_settings()
        self.timeout = self.settings.timeout
        self.max_reintentos = self.settings.max_reintentos
        
    async def procesar(self, parametro: str) -> RespuestaServicio:
        """
        Método principal de procesamiento
        
        Args:
            parametro: Parámetro de entrada
            
        Returns:
            RespuestaServicio con los datos procesados
        """
        try:
            # Tu lógica de negocio aquí
            resultado = await self._realizar_procesamiento(parametro)
            
            return RespuestaServicio(
                datos=resultado,
                estado="exitoso",
                mensaje="Procesamiento completado"
            )
            
        except Exception as e:
            logger.error(f"Error procesando {parametro}: {str(e)}")
            return RespuestaServicio(
                estado="error",
                mensaje=str(e)
            )
    
    async def _realizar_procesamiento(self, parametro: str) -> MiModelo:
        """Lógica interna de procesamiento"""
        
        # Ejemplo: hacer petición HTTP
        if self.settings.api_url:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.settings.api_url}/data/{parametro}")
                response.raise_for_status()
                data = response.json()
        else:
            # Lógica local sin API externa
            data = {"id": parametro, "nombre": f"Procesado: {parametro}"}
        
        # Crear modelo validado
        return MiModelo(
            id=data["id"],
            nombre=data["nombre"],
            # ... más campos según tu modelo
        )
    
    async def validar_parametro(self, parametro: str) -> bool:
        """Validar parámetro de entrada"""
        if not parametro or len(parametro) < 3:
            return False
        return True
```

---

## 📄 Configuración Claude Code

### **claude-config.json**:
```json
{
  "mcpServers": {
    "mi-servicio": {
      "command": "python",
      "args": ["C:\\ruta\\completa\\a\\tu\\proyecto\\mcp_server.py"],
      "transport": "stdio",
      "env": {
        "MI_SERVICIO_DEBUG": "true"
      }
    }
  }
}
```

### **Uso con Claude Code:**
```bash
claude --mcp-config claude-config.json
```

---

## 🧪 Plantilla de Tests

### **tests/test_server.py**:
```python
"""
Tests básicos para el servidor MCP
"""

import pytest
import asyncio
from services.core_service import CoreService
from models.data_models import MiModelo

@pytest.fixture
def core_service():
    """Fixture del servicio principal"""
    return CoreService()

@pytest.mark.asyncio
async def test_procesamiento_basico(core_service):
    """Test básico de procesamiento"""
    resultado = await core_service.procesar("test123")
    
    assert resultado.estado == "exitoso"
    assert resultado.datos is not None
    assert isinstance(resultado.datos, MiModelo)

@pytest.mark.asyncio
async def test_validacion_parametros(core_service):
    """Test de validación de parámetros"""
    # Parámetro válido
    assert await core_service.validar_parametro("abc123") == True
    
    # Parámetro inválido
    assert await core_service.validar_parametro("ab") == False
    assert await core_service.validar_parametro("") == False

def test_modelo_validacion():
    """Test de validación del modelo"""
    # Modelo válido
    modelo = MiModelo(id="TEST123", nombre="Test")
    assert modelo.id == "TEST123"
    
    # Modelo inválido debería lanzar excepción
    with pytest.raises(ValueError):
        MiModelo(id="ab", nombre="Test")  # ID muy corto

# Ejecutar tests: uv run --locked pytest -q
```

---

## 🚀 Configuración de Variables de Entorno

### **.env.example**:
```bash
# Configuración del servicio
MI_SERVICIO_APP_NAME="Mi Servicio MCP"
MI_SERVICIO_DEBUG=false
MI_SERVICIO_LOG_LEVEL=INFO

# API externa (si aplica)
MI_SERVICIO_API_URL=https://api.ejemplo.com
MI_SERVICIO_API_KEY=tu-api-key-aqui
MI_SERVICIO_TIMEOUT=30

MI_SERVICIO_MAX_REINTENTOS=3
```

---

## 📚 Checklist de Desarrollo MCP

### ✅ **Estructura Básica:**
- [ ] `mcp_server.py` creado con plantilla
- [ ] `claude-config.json` configurado
- [ ] `pyproject.toml` y `uv.lock` sincronizados
- [ ] Estructura de carpetas establecida

### ✅ **Funcionalidad Core:**
- [ ] Al menos 1 herramienta MCP implementada
- [ ] Validación de parámetros con Pydantic
- [ ] Manejo de errores robusto
- [ ] Logging configurado

### ✅ **Configuración:**
- [ ] Variables de entorno definidas
- [ ] `.env.example` creado
- [ ] Settings centralizados

### ✅ **Testing:**
- [ ] Tests básicos implementados
- [ ] Script de test de conectividad
- [ ] Validación de modelos testeada

### ✅ **Documentación:**
- [ ] README.md con instrucciones claras
- [ ] Ejemplos de uso incluidos
- [ ] Troubleshooting documentado

---

## 🚨 Errores Comunes y Soluciones

### **Error: "MCP no encontrado"**
```bash
# Solución:
uv sync --locked
```

### **Error: "Transport stdio not supported"**
```python
# Problema: Usando servidor web en lugar de stdio
# Solución: Usar mcp.server.stdio.stdio_server()
```

### **Error: "Tool not found"**
```python
# Verificar que el nombre en @server.call_tool() coincida exactamente
# con el nombre en types.Tool()
```

### **Error: "Invalid JSON response"**
```python
# Asegurar que siempre retornas List[types.TextContent]
return [types.TextContent(type="text", text=resultado)]
```

---

## 🎯 Mejores Prácticas

### **Diseño de Herramientas:**
1. **Nombres claros:** `consultar_datos` mejor que `cd`
2. **Descripciones detalladas:** Explica qué hace exactamente
3. **Validación robusta:** Usa Pydantic para todos los inputs
4. **Respuestas estructuradas:** JSON bien formateado

### **Manejo de Errores:**
1. **Nunca crashes:** Siempre captura excepciones
2. **Mensajes útiles:** Errores descriptivos para el usuario
3. **Logging completo:** Log todos los errores para debugging
4. **Fallbacks:** Comportamiento por defecto cuando algo falla

### **Performance:**
1. **Async/await:** Todas las operaciones I/O deben ser asíncronas
2. **Timeouts:** Siempre configura timeouts para APIs externas
3. **Rate limiting:** Respeta límites de APIs externas
4. **Caching:** Cache resultados cuando sea apropiado

### **Seguridad:**
1. **Validación de entrada:** Nunca confíes en datos externos
2. **API keys seguras:** Usa variables de entorno
3. **Sanitización:** Limpia datos antes de procesarlos
4. **Logging seguro:** No loggees datos sensibles

---

## 🔄 Proceso de Desarrollo Estándar

### **Paso 1: Planificación**
1. Define qué herramientas va a ofrecer tu MCP
2. Identifica APIs o servicios externos necesarios
3. Diseña los modelos de datos con Pydantic
4. Planifica la estructura de carpetas

### **Paso 2: Implementación**
1. Copia las plantillas de esta guía
2. Reemplaza `[MI_SERVICIO]` con tu nombre real
3. Implementa tu lógica en `services/core_service.py`
4. Define modelos en `models/data_models.py`
5. Configura variables en `config/settings.py`

### **Paso 3: Testing**
1. Crea tests básicos
2. Ejecuta `uv run --locked python mcp_server.py` para verificar que inicia
3. Prueba con `claude --mcp-config claude-config.json`
4. Valida todas las herramientas funcionan

### **Paso 4: Documentación**
1. Crea README.md con instrucciones
2. Documenta todas las herramientas
3. Incluye ejemplos de uso
4. Añade troubleshooting común

### **Paso 5: Refinamiento**
1. Optimiza performance si es necesario
2. Añade logging detallado
3. Mejora manejo de errores
4. Añade más tests

---

## 🎉 ¡Ejemplo Completo Funcional!

Con estas plantillas puedes crear un servidor MCP funcional en minutos:

1. **Copia todas las plantillas**
2. **Reemplaza `[MI_SERVICIO]` con tu nombre**
3. **Implementa tu lógica específica**
4. **Ejecuta y prueba**

**Esta guía garantiza que cualquier LLM pueda crear un servidor MCP 100% funcional siguiendo estos patrones estándar.**

---

## 📞 Verificación Final

Tu servidor MCP está listo cuando:

✅ `uv run --locked python mcp_server.py` ejecuta sin errores
✅ `claude --mcp-config claude-config.json` se conecta  
✅ Claude puede listar y usar tus herramientas  
✅ Los tests pasan: `uv run --locked pytest -q`
✅ La documentación está completa  

**¡Congratulations! Tienes un servidor MCP 100% funcional y profesional.**
