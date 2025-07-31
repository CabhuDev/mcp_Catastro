# 📖 Guía de Usuario - Servidor MCP Catastro Completo

## 🎯 Introducción

**Servidor MCP (Model Context Protocol) 100% profesional** con **15 herramientas especializadas** para consultar datos del **Catastro de España** directamente desde **Claude Code**. 

### ✨ **NOVEDADES v4.0.0**
- 🗺️ **Geometrías WFS** - Polígonos precisos de parcelas
- 🏘️ **MetaParcelas** - Parcelas con múltiples referencias
- 📄 **Export GeoJSON** - Compatible con aplicaciones de mapas
- 🚀 **Sistema de Cache** - Optimización automática de consultas frecuentes

---

## 🚀 Instalación y Configuración

### 📋 Prerrequisitos
- Python 3.11+
- Claude Code instalado

### 🔧 Instalación

1. **Instalar dependencias:**
```powershell
cd C:\Users\Pablo\Desktop\obratec_app\mcp_catastro
pip install -r requirements.txt
```

2. **Configurar entorno (opcional):**
```powershell
cp .env.example .env
# Editar .env para configurar OpenAI API key si deseas IA real
```

3. **Ejecutar servidor MCP:**
```powershell
python mcp_server.py
```

4. **Configurar Claude Code:**
```powershell
# Opción A: Usar archivo de configuración (recomendado)
claude --mcp-config claude-config.json

# Opción B: Configuración directa
claude --mcp-config '{"mcpServers":{"catastro":{"command":"python","args":["C:\\Users\\Pablo\\Desktop\\obratec_app\\mcp_catastro\\mcp_server.py"],"transport":"stdio"}}}'
```

---

## 🛠️ Herramientas MCP Disponibles - 15 Herramientas Profesionales

### **🎯 CONSULTAS BÁSICAS**

### 1. **Consultar por Referencia Catastral**
```
Herramienta: consultar_catastro_por_referencia
Entrada: referencia catastral de 20 caracteres
```

**Ejemplo con Claude Code:**
```
Usuario: "Consulta la referencia catastral 2749704YJ0624N0001DI"

Claude usará automáticamente la herramienta y mostrará:
- Datos básicos del inmueble
- Dirección catastral completa
- Superficie construida y útil
- Año de construcción
- Uso del inmueble (residencial/comercial/industrial)
- Valor catastral
```

### 2. **Consultar Parcela por Código (División Horizontal)**
```
Herramienta: consultar_parcela_por_codigo
Entrada: código de parcela de 14 caracteres
```

**Ejemplo con Claude Code:**
```
Usuario: "Lista todos los inmuebles de la parcela 2314501EG1421S"

Claude mostrará:
- Lista completa de inmuebles en la parcela
- Coeficientes de participación
- Escaleras, plantas y puertas
- Usos específicos de cada inmueble
- Referencias catastrales completas
```

### 3. **Consultar por Coordenadas**
```
Herramienta: consultar_catastro_por_coordenadas  
Entrada: latitud y longitud (España: 35-44°N, -10-5°E)
```

**Ejemplo con Claude Code:**
```
Usuario: "¿Qué inmueble hay en las coordenadas 40.4168, -3.7038?"

Claude encontrará automáticamente:
- Referencia catastral del inmueble
- Datos completos de la parcela
- Información de construcción y ubicación
```

---

### **🗺️ LISTADOS Y NAVEGACIÓN**

### 4. **Listar Provincias**
```
Herramienta: listar_provincias
Entrada: ninguna (lista completa)
```

**Ejemplo con Claude Code:**
```
Usuario: "Lista todas las provincias de España"

Claude mostrará:
- 52 provincias españolas oficiales
- Nombres normalizados
- Total de provincias disponibles
```

### 5. **Listar Municipios**
```
Herramienta: listar_municipios
Entrada: provincia + filtro opcional
```

**Ejemplo con Claude Code:**
```
Usuario: "Lista los municipios de Granada que empiecen por 'B'"

Claude mostrará:
- BAZA, BENALUA, BENAMAUREL, etc.
- Filtrado inteligente
- Total de municipios encontrados
```

### 6. **Listar Calles**
```
Herramienta: listar_calles
Entrada: provincia + municipio
```

**Ejemplo con Claude Code:**
```
Usuario: "Lista las calles de Baza, Granada"

Claude mostrará:
- Callejero completo del municipio
- Tipos de vía (CL, AV, PZ, etc.)
- Nombres oficiales normalizados
```

---

### **🔄 CONVERSIONES GEOESPACIALES**

### 7. **Coordenadas → Referencia Catastral**
```
Herramienta: convertir_coordenadas_a_referencia
Entrada: latitud, longitud, sistema de referencia
```

**Ejemplo con Claude Code:**
```
Usuario: "¿Cuál es la referencia catastral de las coordenadas 40.4168, -3.7038?"

Claude convertirá automáticamente:
- Coordenadas GPS → Referencia catastral
- Validación de coordenadas dentro de España
- Soporte para múltiples sistemas de referencia
```

### 8. **Referencia Catastral → Coordenadas**
```
Herramienta: convertir_referencia_a_coordenadas
Entrada: referencia catastral, sistema de referencia
```

**Ejemplo con Claude Code:**
```
Usuario: "¿Dónde está ubicada la referencia 4418928VG4141G0001IW?"

Claude calculará:
- Coordenadas del centroide de la parcela
- Ubicación GPS precisa
- Validación de formato de referencia
```

### 9. **Geocodificar Dirección**
```
Herramienta: geocodificar_direccion
Entrada: dirección en texto + municipio opcional
```

**Ejemplo con Claude Code:**
```
Usuario: "¿Dónde está Gran Vía 1, Madrid?"

Claude geocodificará usando CartoCiudad:
- Coordenadas precisas de la dirección
- Referencia catastral asociada
- Validación mediante IGN
```

---

### **🔧 FUNCIONALIDADES AVANZADAS** ✨ **NUEVAS**

### 10. **Obtener Geometría de Parcela** ✨
```
Herramienta: obtener_geometria_parcela
Entrada: referencia catastral + sistema de referencia
```

**Ejemplo con Claude Code:**
```
Usuario: "Obtén la geometría completa de la parcela 4418928VG4141G0001IW"

Claude obtendrá mediante WFS:
- Polígono preciso de la parcela
- Coordenadas de todos los vértices
- Centroide calculado
- Superficie en metros cuadrados
- Compatible con aplicaciones GIS
```

### 11. **Consultar MetaParcela** ✨
```
Herramienta: consultar_metaparcela
Entrada: referencia base O componentes (provincia/municipio/polígono/parcela)
```

**Ejemplo con Claude Code:**
```
Usuario: "Consulta la MetaParcela de Madrid, municipio Madrid, polígono 1, parcela 1"

Claude analizará:
- Todas las parcelas que componen la MetaParcela
- Información catastral completa de cada una
- Geometrías individuales
- Referencias catastrales múltiples
```

### 12. **Exportar Geometría GeoJSON** ✨
```
Herramienta: exportar_geometria_geojson
Entrada: referencia catastral
```

**Ejemplo con Claude Code:**
```
Usuario: "Exporta la geometría de la parcela 4418928VG4141G0001IW en formato GeoJSON"

Claude generará:
- GeoJSON estándar completo
- Compatible con Leaflet, OpenLayers, QGIS
- Propiedades de la parcela incluidas
- Listo para usar en aplicaciones web de mapas
```

---

### **🛠️ HERRAMIENTAS DE SOPORTE**

### 13. **Validar Referencia Catastral**
```
Herramienta: validar_referencia_catastral
Entrada: referencia de 14 o 20 caracteres
```

**Ejemplo con Claude Code:**
```
Usuario: "Valida la referencia 2314501EG1421S"

Claude analizará:
- Formato correcto (14 o 20 caracteres)
- Componentes: provincia, municipio, sector, manzana, parcela
- Estado de validación
- Sugerencias para completar si es parcial
```

### 14. **Generar Resumen IA**
```
Herramienta: generar_resumen_ia
Entrada: referencia + opciones (idioma, usar_openai)
```

**Ejemplo con Claude Code:**
```
Usuario: "Haz un resumen profesional de la referencia 2749704YJ0624N0001DI"

Claude generará:
📋 RESUMEN PROFESIONAL CATASTRAL
**Referencia:** 2749704YJ0624N0001DI
**Tipo:** Vivienda unifamiliar
**Superficie:** 92 m² construidos
**Antigüedad:** 17 años (2007)
**Ubicación:** Zona residencial consolidada
🏠 **Valoración:** Inmueble contemporáneo en buen estado
```

### 15. **Buscar por Dirección (Informativo)**
```
Herramienta: buscar_catastro_por_direccion
Entrada: dirección completa
```

**Ejemplo con Claude Code:**
```
Usuario: "Busca CALLE REYES CATOLICOS 6, 18100, ARMILLA, GRANADA"

Claude explicará:
- Limitaciones de la búsqueda por dirección
- Alternativas funcionales disponibles
- Recomendaciones para obtener la referencia catastral
- Enlaces a recursos oficiales
```
```
Herramienta: validar_referencia_catastral
Entrada: referencia a validar
```

**Ejemplo con Claude Code:**
```
Usuario: "¿Es válida la referencia 1234567AB1234C1234DE?"

Claude responderá:
"Referencia catastral válida: 1234567AB1234C1234DE"
```

---

## 💡 Ejemplos de Uso con Claude Code

### **Consultas Naturales:**
- "¿Qué datos tiene esta referencia catastral?"
- "Consulta qué hay en Madrid centro"  
- "Resume los datos de esta parcela"
- "Busca por coordenadas y luego haz un resumen"

### **Preguntas Específicas:**
- "¿Cuál es el uso de la referencia 2749704YJ0624N0001DI?"
- "¿Qué superficie tiene el inmueble en las coordenadas 40.4168, -3.7038?"
- "Valida esta referencia: 9872023VH5797H0001JU"

### **Análisis Complejos:**
- "Compara estas dos referencias catastrales"
- "Busca inmuebles cerca de esta coordenada"
- "Explícame el formato de las referencias catastrales"

---

## 🧠 Sistema de IA Integrado

### 🎭 **Modo Simulado** (por defecto)
- ✅ **Sin coste** - No requiere API keys
- 🚀 **Respuesta instantánea** - Procesamiento local
- 📊 **Análisis automático** - Interpreta datos catastrales
- 🌍 **Multiidioma** - Español, inglés, catalán

### 🧮 **Modo OpenAI** (opcional)
- 🔑 **Requiere API key** - Configura en `.env`
- 🧠 **Análisis avanzado** - Mayor precisión y contexto
- 💰 **Coste por uso** - Según tarifas OpenAI
- 🎯 **Resúmenes profesionales** - Calidad superior

### 📝 **Configurar OpenAI:**
```powershell
# En archivo .env
CATASTRO_OPENAI_API_KEY=sk-tu-clave-aqui
CATASTRO_OPENAI_MODEL=gpt-4
CATASTRO_OPENAI_TEMPERATURE=0.3
```

---

## 📝 Referencias Catastrales - Formato Oficial

### ✅ **Formato Válido (20 caracteres):**
```
2749704YJ0624N0001DI
│││││││││││││││││││└── 2 letras: dígitos control
│││││││││││││││└────── 4 dígitos: subparcela  
││││││││││││└────────── 1 letra: coordenada Z
│││││││││└─────────────── 4 dígitos: coordenada Y
│││││└──────────────────── 2 letras: coordenada X
└────────────────────────── 7 dígitos: identificador parcela
```

### ❌ **Formatos Inválidos:**
- `2749704YJ0624N0001` (muy corta, falta DI)
- `2749704YJ0624N0001DI5` (muy larga)  
- `2749704yj0624n0001di` (minúsculas no permitidas)
- `A749704YJ0624N0001DI` (letra en posición numérica)

### 📋 **Referencias de Prueba:**
```
2749704YJ0624N0001DI  # Madrid ejemplo
4707801YJ0675N0001JE  # Barcelona ejemplo  
8077801YJ0687N0001LE  # Valencia ejemplo
```

---

## 🌍 Coordenadas Válidas para España

### ✅ **Rangos Válidos:**
- **Latitud:** 35.0° - 44.0° Norte
- **Longitud:** -10.0° - 5.0° Este

### 📍 **Coordenadas de Prueba:**
```
Madrid Centro:    40.4168, -3.7038
Barcelona:        41.3851, 2.1734
Valencia:         39.4699, -0.3763
Sevilla:          37.3891, -5.9845
Bilbao:           43.2627, -2.9253
```

---

## 🚨 Resolución de Problemas

### **Errores Comunes:**

| Error | Causa | Solución |
|-------|-------|----------|
| `Bibliotecas MCP no encontradas` | `mcp` no instalado | `pip install mcp` |
| `Referencia catastral inválida` | Formato incorrecto | Verificar 20 caracteres y patrón |
| `Coordenadas fuera de rango` | No están en España | Usar rangos válidos |
| `Servicio no disponible` | Catastro caído | Reintentar más tarde |
| `Timeout` | Respuesta lenta | Aumentar `CATASTRO_TIMEOUT` en `.env` |

### **Diagnóstico:**

```powershell
# Probar conectividad
python scripts/test-connection.py

# Verificar configuración
python -c "from config.settings import get_settings; print(get_settings().catastro_base_url)"

# Debug mode
# En .env: CATASTRO_DEBUG=true
```

---

## 🧪 Testing y Verificación

### **Pruebas Rápidas:**
```powershell
# Test completo de conectividad
python scripts/test-connection.py

# Tests unitarios
pytest tests/ -v

# Test específico de validación
pytest tests/test_catastro.py::TestReferenciaCatastral -v
```

### **Verificar que todo funciona:**
1. `python mcp_server.py` (debe iniciar sin errores)
2. En otra terminal: `claude --mcp-config claude-config.json`
3. Preguntar a Claude: "Valida la referencia 2749704YJ0624N0001DI"

---

## ⚙️ Configuración Avanzada

### **Variables de Entorno Principales:**
```bash
# Configuración básica
CATASTRO_DEBUG=true                    # Activar logs detallados
CATASTRO_LOG_LEVEL=DEBUG               # Nivel de logging
CATASTRO_CATASTRO_TIMEOUT=60           # Timeout en segundos

# Rate limiting
CATASTRO_MAX_REQUESTS_PER_MINUTE=30    # Reducir si hay problemas

# OpenAI (opcional)
CATASTRO_OPENAI_API_KEY=sk-xxx         # Tu API key
CATASTRO_OPENAI_MODEL=gpt-3.5-turbo    # Modelo a usar
```

### **Personalización de Logs:**
```bash
# Crear logs más detallados
CATASTRO_LOG_LEVEL=DEBUG

# Los logs se guardan en:
logs/catastro_mcp.log
```

---

## ❓ Preguntas Frecuentes

**P: ¿Necesito Docker para ejecutar MCP?**
R: No, MCP se ejecuta localmente con Python. Docker era innecesario.

**P: ¿Funciona sin conexión a internet?**
R: No, necesita acceso a `ovc.catastro.meh.es`

**P: ¿Puedo consultar catastros de otros países?**  
R: No, solo España y territorios españoles

**P: ¿Los resúmenes IA cuestan dinero?**
R: El modo simulado es gratis. OpenAI requiere API key de pago.

**P: ¿Hay límites de consultas?**
R: Sí, 60 por minuto por defecto. Configurable en `.env`.

**P: ¿Cómo sé si está funcionando?**
R: Ejecuta `python scripts/test-connection.py` para verificar.

---

## 🆘 Soporte y Ayuda

### **Recursos:**
- **Logs:** `logs/catastro_mcp.log`
- **Config:** `claude-config.json`
- **Tests:** `python scripts/test-connection.py`
- **Docs:** Carpeta `docs/`

### **Comandos Útiles:**
```powershell
# Verificar instalación
python -c "import mcp; print('MCP OK')"

# Ver configuración actual
python -c "from config.settings import get_settings; s=get_settings(); print(f'URL: {s.catastro_base_url}')"

# Test rápido de referencia
python -c "from models.catastro_models import ReferenciaCatastral; print(ReferenciaCatastral.validar_formato_estatico('2749704YJ0624N0001DI'))"
```

---

## 🎉 ¡Todo Listo!

1. `pip install -r requirements.txt`
2. `python mcp_server.py`  
3. `claude --mcp-config claude-config.json`
4. **Pregunta a Claude sobre cualquier referencia catastral**

¡Disfruta de tu servidor MCP 100% funcional para el Catastro de España!