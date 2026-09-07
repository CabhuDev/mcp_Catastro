# 🤝 Contribuir a MCP Catastro España

¡Gracias por tu interés en contribuir! Este proyecto utiliza la API oficial del Catastro de España para proporcionar acceso programático a datos catastrales a través del protocolo MCP.

## 🚀 Empezar Rápido

### 📋 Prerrequisitos

- **Python 3.14**
- **Git**
- **Claude Code** (para testing)

### 🔧 Configuración Desarrollo

```bash
# 1. Fork y clonar
git clone https://github.com/CabhuDev/mcp_Catastro.git
cd mcp_Catastro

# 2. Instalar exactamente el entorno bloqueado
uv sync --locked --all-extras --dev
```

## 🧪 Testing

### Tests Unitarios
```bash
# Ejecutar todos los tests
uv run --locked pytest -q

# Tests con cobertura
uv run --locked pytest --cov=services --cov=models --cov=mcp_server --cov-report=html

# Test específico
uv run --locked pytest -q
```

### Tests de Integración
```bash
# Test con API real del Catastro
python -c "
import asyncio
from services.catastro_service import CatastroService
async def test():
    service = CatastroService()
    result = await service.consultar_por_referencia('2314501EG1421S0001KJ')
    print(f'Estado: {result.estado_consulta}')
asyncio.run(test())
"

# Test del servidor MCP
uv run --locked python mcp_server.py &
# ... probar herramientas MCP ...
kill %1
```

## 🎯 Áreas de Contribución

### 🐛 Bugs y Fixes
- Manejo de errores de la API del Catastro
- Parsing de estructuras JSON/XML
- Validación de referencias catastrales
- Timeouts y reconexiones

### ✨ Nuevas Características
- **Consultas por polígono** - Inmuebles rústicos
- **Búsqueda por provincia/municipio** - Listados
- **Cache inteligente** - Optimización consultas
- **Métricas avanzadas** - Estadísticas de uso
- **Exportación de datos** - CSV, Excel, PDF

### 📚 Documentación
- Ejemplos de uso avanzado
- Guías de integración
- Casos de uso específicos
- Documentación API

### 🚀 Optimización
- Mejoras de rendimiento
- Reducción de dependencias
- Optimización de memoria
- Paralelización de consultas

## 📝 Estándares de Código

### Formato y Estilo
```bash
# Auto-formato con Black
black services/ models/ tests/

# Ordenar imports
isort services/ models/ tests/

# Linting
flake8 services/ models/ tests/

# Type checking
mypy services/ models/
```

### Estándares
- **PEP 8** - Estilo de código Python
- **Pydantic V2** - Validación de datos
- **Type hints** - Tipado completo
- **Docstrings** - Documentación en funciones
- **Tests** - Cobertura mínima 80%

### Convenciones de Naming
```python
# Clases: PascalCase
class CatastroService:
    pass

# Funciones y variables: snake_case
def consultar_por_referencia():
    referencia_catastral = "..."

# Constantes: UPPER_SNAKE_CASE
CONSULTA_DNPRC = "/api/endpoint"

# Archivos: snake_case.py
catastro_service.py
```

## 🔀 Workflow de Contribución

### 1. Crear Issue
```markdown
## 🐛 Bug Report / ✨ Feature Request

**Descripción:**
Descripción clara del problema o característica

**Reproducir:**
1. Paso 1
2. Paso 2
3. Error/resultado esperado

**Entorno:**
- Python: 3.14.x
- OS: Windows/Linux/Mac
- MCP Version: x.x.x
```

### 2. Crear Branch
```bash
# Features
git checkout -b feature/nueva-funcionalidad

# Bug fixes
git checkout -b fix/corregir-error

# Documentación
git checkout -b docs/actualizar-readme
```

### 3. Desarrollo
```bash
# Hacer cambios
# ...

# Verificar tests
uv run --locked pytest -q

# Verificar formato
black --check services/ models/
flake8 services/ models/

# Commit
git add .
git commit -m "feat: añadir consulta por polígono"
```

### 4. Pull Request
```markdown
## 📝 Descripción

Resumen claro de los cambios realizados.

## 🧪 Testing

- [ ] Tests unitarios añadidos/actualizados
- [ ] Tests de integración verificados
- [ ] Documentación actualizada

## ✅ Checklist

- [ ] Código formateado con Black
- [ ] Imports ordenados con isort
- [ ] Sin errores de flake8
- [ ] Type hints añadidos
- [ ] Docstrings actualizados
- [ ] Tests pasan
```

## 🏛️ Estructura API del Catastro

### Endpoints Oficiales
```python
# Base URL
BASE_URL = "https://ovc.catastro.meh.es"

# Consultas por referencia
CONSULTA_DNPRC = "/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/json/Consulta_DNPRC"

# Consultas por coordenadas  
CONSULTA_RCCOOR = "/OVCServWeb/OVCWcfCoord/COVCCoordenadas.svc/json/Consulta_RCCOOR"
```

### Estructuras de Datos
```python
# Respuesta 20 caracteres (inmueble específico)
{
  "consulta_dnprcResult": {
    "bico": {
      "bi": {
        "debi": {...},  # Datos básicos
        "dt": {...}     # Dirección y ubicación
      }
    }
  }
}

# Respuesta 14 caracteres (división horizontal)
{
  "consulta_dnprcResult": {
    "lrcdnp": {
      "rcdnp": [...]  # Array de inmuebles
    }
  }
}
```

## 🚨 Limitaciones Conocidas

### API del Catastro
- **Timeouts:** Respuestas lentas ocasionales
- **Búsqueda por dirección:** No disponible de forma fiable
- **Datos históricos:** Solo datos actuales

### Proyecto
- **Cobertura geográfica:** Solo España
- **Formato referencias:** Solo formato actual español
- **OpenAI:** Coste adicional para IA real

## 📊 Logging y observabilidad futura

### Logging
```python
import logging
logger = logging.getLogger(__name__)

# Ejemplos
logger.info("Consulta completada endpoint=%s estado=%d", endpoint, estado)
```

Los datos catastrales se ocultan por defecto. Para diagnósticos controlados se
requieren conjuntamente `CATASTRO_LOG_LEVEL=DEBUG` y
`CATASTRO_LOG_SENSITIVE_DATA=true`. El proyecto todavía no exporta métricas ni
implementa caché o rate limiting; esas capacidades están en el roadmap.

## 🆘 Obtener Ayuda

### Documentación
- **README principal:** [README.md](README.md)
- **API del Catastro:** [Guia_Completa_API_Catastro.md](Guia_Completa_API_Catastro.md)
- **Desarrollo MCP:** [docs/MCP_DEVELOPMENT_GUIDE.md](docs/MCP_DEVELOPMENT_GUIDE.md)

### Contacto
- **Issues:** [GitHub Issues](https://github.com/CabhuDev/mcp_Catastro/issues)
- **Discussions:** [GitHub Discussions](https://github.com/CabhuDev/mcp_Catastro/discussions)

### Debug
```bash
# Logs detallados
export CATASTRO_DEBUG=true
export CATASTRO_LOG_LEVEL=DEBUG
uv run --locked python mcp_server.py

# Test conectividad
python -c "import httpx; print(httpx.get('https://ovc.catastro.meh.es').status_code)"
```

## 📝 Templates

### Bug Report
```markdown
**🐛 Descripción del Bug**
Descripción clara y concisa del error.

**🔄 Reproducir**
Pasos para reproducir el error:
1. Ir a '...'
2. Hacer clic en '....'
3. Ver error

**✅ Comportamiento Esperado**
Descripción de lo que debería pasar.

**📱 Entorno**
- OS: [ej. Windows 11]
- Python: [ej. 3.14.1]
- MCP Catastro: [ej. 3.0.0]

**📋 Logs**
```
Incluir logs relevantes aquí
```
**🔍 Información Adicional**
Cualquier otra información útil.
```

### Feature Request
```markdown
**✨ Descripción de la Característica**
Descripción clara de la nueva funcionalidad.

**🎯 Problema que Resuelve**
¿Qué problema resuelve esta característica?

**💡 Solución Propuesta**
Descripción de cómo debería funcionar.

**🔄 Alternativas Consideradas**
Otras soluciones que has considerado.

**📊 Casos de Uso**
Ejemplos específicos de uso.
```

---

<div align="center">

**¡Gracias por contribuir al proyecto! 🙌**

[![Contributors](https://img.shields.io/github/contributors/CabhuDev/mcp_Catastro.svg)](https://github.com/CabhuDev/mcp_Catastro/graphs/contributors)

</div>
