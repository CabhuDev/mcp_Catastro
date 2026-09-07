# 🚀 Servidor MCP Catastro - 100% Puro

## 🎯 **MCP REAL PARA CLAUDE CODE**

Servidor MCP completamente limpio y funcional para consultas al **Catastro de España**.

---

## 🔧 **Instalación y Uso:**

### **1. Instalar dependencias:**
```powershell
cd C:\Users\Pablo\Desktop\obratec_app\mcp_catastro
uv sync --locked
```

### **2. Ejecutar servidor MCP:**
```powershell
uv run --locked python mcp_server.py
```

### **3. Configurar Claude Code:**
```powershell
# Usando archivo de configuración (recomendado)
claude --mcp-config claude-config.json

# O configuración directa
claude --mcp-config claude-config.json
```

---

## 🛠️ **Herramientas MCP Disponibles:**

### 1. **Consultar por referencia catastral**
```
consultar_catastro_por_referencia
Entrada: referencia (ej: "2749704YJ0624N0001DI")
```

### 2. **Consultar por coordenadas**
```
consultar_catastro_por_coordenadas  
Entrada: latitud, longitud (ej: 40.4168, -3.7038)
```

### 3. **Generar resumen IA**
```
generar_resumen_ia
Entrada: referencia, usar_openai, idioma
```

### 4. **Validar referencia**
```
validar_referencia_catastral
Entrada: referencia a validar
```

---

## 🧪 **Pruebas:**

```powershell
# Probar conectividad con Catastro
uv run --locked python tests/test-startup.py

# Tests unitarios
uv run --locked pytest -q
```

---

## ⚙️ **Configuración (opcional):**

Crea `.env` desde `.env.example` para:
- Configurar OpenAI API key (para IA real)
- Ajustar timeouts y reintentos
- Habilitar debug mode
- Mantener ocultos los datos sensibles en logs por defecto

---

## 📁 **Estructura Simplificada:**

```
mcp_catastro/
├── 🚀 mcp_server.py          # Servidor MCP principal
├── 🔧 services/              # Lógica de consultas
├── 📊 models/                # Modelos de datos
├── ⚙️ config/                # Configuración
├── 🧪 tests/                 # Tests
├── 📖 docs/                  # Documentación
├── 📄 claude-config.json     # Config Claude Code
├── 📋 pyproject.toml          # Dependencias directas
└── 🔒 uv.lock                 # Dependencias bloqueadas
```

---

## ✅ **Características:**

- ✅ **MCP 100% real** - Compatible con Claude Code
- ✅ **API WCF oficial** - Endpoints actualizados del Catastro
- ✅ **Dependencias mínimas** - Solo lo esencial
- ✅ **Sin Docker** - Ejecuta localmente como debe ser
- ✅ **4 herramientas** - Consultas completas al Catastro
- ✅ **IA integrada** - Resúmenes automáticos o con OpenAI

---

## 🎉 **¡Listo para usar con Claude Code!**

1. `uv sync --locked`
2. `uv run --locked python mcp_server.py`
3. `claude --mcp-config claude-config.json`
4. Pregunta a Claude sobre cualquier referencia catastral
