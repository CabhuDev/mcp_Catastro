#!/usr/bin/env python3
"""
Servidor MCP REAL para Catastro de España - Compatible con Claude Code
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder para manejar objetos datetime"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def parse_direccion_completa(direccion: str) -> dict:
    """
    Parsea una dirección completa en formato esperado
    Ejemplo: 'CALLE REYES CATOLICOS 6, 18100, ARMILLA, GRANADA'
    """
    try:
        # Limpiar y dividir por comas
        partes = [parte.strip().upper() for parte in direccion.split(',')]
        
        if len(partes) < 3:
            return {
                "error": "Formato incorrecto. Use: 'TIPO_VIA NOMBRE_VIA NUMERO, CODIGO_POSTAL, MUNICIPIO, PROVINCIA'",
                "direccion_original": direccion
            }
        
        # Parte 1: Vía completa (TIPO_VIA NOMBRE_VIA NUMERO)
        via_completa = partes[0].strip()
        
        # Intentar extraer tipo de vía común
        tipos_via = ["CALLE", "AVENIDA", "PLAZA", "PASEO", "CARRETERA", "CAMINO", "TRAVESIA", "GLORIETA", "CL", "AV", "PZ", "PS", "CR"]
        tipo_via = "CALLE"  # Default
        nombre_via = via_completa
        numero = ""
        
        # Buscar tipo de vía al inicio
        for tipo in tipos_via:
            if via_completa.startswith(tipo + " "):
                tipo_via = tipo if tipo not in ["CL", "AV", "PZ", "PS", "CR"] else {"CL": "CALLE", "AV": "AVENIDA", "PZ": "PLAZA", "PS": "PASEO", "CR": "CARRETERA"}[tipo]
                resto_via = via_completa[len(tipo):].strip()
                
                # Extraer número del final
                palabras = resto_via.split()
                if palabras and palabras[-1].replace('-', '').replace('/', '').isalnum():
                    numero = palabras[-1]
                    nombre_via = " ".join(palabras[:-1])
                else:
                    nombre_via = resto_via
                break
        
        # Si no encontró tipo de vía, asumir que toda la primera parte es nombre + número
        if tipo_via == "CALLE" and nombre_via == via_completa:
            palabras = via_completa.split()
            if palabras and palabras[-1].replace('-', '').replace('/', '').isalnum():
                numero = palabras[-1]
                nombre_via = " ".join(palabras[:-1])
            else:
                nombre_via = via_completa
        
        # Extraer resto de componentes
        if len(partes) == 3:
            # Formato: VIA, MUNICIPIO, PROVINCIA
            codigo_postal = ""
            municipio = partes[1].strip()
            provincia = partes[2].strip()
        elif len(partes) == 4:
            # Formato: VIA, CODIGO_POSTAL, MUNICIPIO, PROVINCIA
            codigo_postal = partes[1].strip()
            municipio = partes[2].strip()
            provincia = partes[3].strip()
        else:
            # Formato: VIA, ?, MUNICIPIO, PROVINCIA (tomar últimos dos como municipio y provincia)
            codigo_postal = ""
            municipio = partes[-2].strip()
            provincia = partes[-1].strip()
        
        return {
            "tipo_via": tipo_via,
            "nombre_via": nombre_via,
            "numero": numero,
            "codigo_postal": codigo_postal,
            "municipio": municipio,
            "provincia": provincia,
            "direccion_original": direccion,
            "parseado_correctamente": True
        }
        
    except Exception as e:
        return {
            "error": f"Error parseando dirección: {str(e)}",
            "direccion_original": direccion,
            "parseado_correctamente": False
        }

# Importar bibliotecas MCP reales (necesitas instalarlas)
try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("ERROR: Bibliotecas MCP no encontradas. Instala con: pip install mcp")

from services.catastro_service import CatastroService
from services.ai_summary import AIService
from models.catastro_models import CatastroResponse, ReferenciaCatastral
from config.settings import get_settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not MCP_AVAILABLE:
    logger.error("Bibliotecas MCP no disponibles. El servidor no funcionará con Claude Code.")
    exit(1)

# Inicializar servicios
settings = get_settings()
catastro_service = CatastroService()
ai_service = AIService()

# Crear servidor MCP REAL
app = Server("catastro-mcp")

@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """Lista todas las herramientas disponibles del servidor MCP"""
    logger.info("🔍 Listando herramientas MCP...")
    
    tools = [
        types.Tool(
            name="consultar_catastro_por_referencia",
            description="Consulta datos catastrales por referencia catastral",
            inputSchema={
                "type": "object",
                "properties": {
                    "referencia": {
                        "type": "string",
                        "description": "Referencia catastral de 20 caracteres alfanuméricos"
                    }
                },
                "required": ["referencia"]
            }
        ),
        types.Tool(
            name="consultar_catastro_por_coordenadas", 
            description="Consulta datos catastrales por coordenadas geográficas",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitud": {
                        "type": "number",
                        "description": "Latitud en grados decimales"
                    },
                    "longitud": {
                        "type": "number", 
                        "description": "Longitud en grados decimales"
                    }
                },
                "required": ["latitud", "longitud"]
            }
        ),
        types.Tool(
            name="generar_resumen_ia",
            description="Genera un resumen profesional de datos catastrales usando IA",
            inputSchema={
                "type": "object",
                "properties": {
                    "referencia": {
                        "type": "string",
                        "description": "Referencia catastral"
                    },
                    "usar_openai": {
                        "type": "boolean",
                        "description": "Usar OpenAI en lugar del modelo simulado",
                        "default": False
                    },
                    "idioma": {
                        "type": "string",
                        "description": "Idioma del resumen",
                        "default": "es"
                    }
                },
                "required": ["referencia"]
            }
        ),
        types.Tool(
            name="validar_referencia_catastral",
            description="Valida y analiza referencias catastrales completas (20 chars) y parciales (14 chars). Proporciona explicaciones detalladas para referencias incompletas y guía para obtener la referencia completa.",
            inputSchema={
                "type": "object",
                "properties": {
                    "referencia": {
                        "type": "string",
                        "description": "Referencia catastral a validar (completa de 20 caracteres o parcial de 14). Ejemplo: '2314501EG1421S' (parcial) o '4418928VG4141G0001IW' (completa)"
                    }
                },
                "required": ["referencia"]
            }
        ),
        types.Tool(
            name="buscar_catastro_por_direccion",
            description="HERRAMIENTA INFORMATIVA: Explica las limitaciones de la búsqueda por dirección del Catastro y proporciona alternativas funcionales. La API del Catastro NO permite búsquedas directas por dirección postal de forma fiable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "direccion_completa": {
                        "type": "string",
                        "description": "Dirección completa incluyendo: TIPO_VIA NOMBRE_VIA NUMERO, CODIGO_POSTAL, MUNICIPIO, PROVINCIA. Ejemplo: 'CALLE REYES CATOLICOS 6, 18100, ARMILLA, GRANADA'"
                    }
                },
                "required": ["direccion_completa"]
            }
        ),
        types.Tool(
            name="consultar_parcela_por_codigo",
            description="Consulta información de parcela catastral usando código de 14 caracteres según método oficial Consulta_DNPRC. Devuelve automáticamente TODOS los inmuebles en parcelas con división horizontal. Ejemplo: '2314501EG1421S'",
            inputSchema={
                "type": "object",
                "properties": {
                    "codigo_parcela": {
                        "type": "string",
                        "description": "Código de parcela de 14 caracteres alfanuméricos (PROVINCIA+MUNICIPIO+SECTOR+MANZANA+PARCELA). Ejemplo: '2314501EG1421S'"
                    }
                },
                "required": ["codigo_parcela"]
            }
        ),
        types.Tool(
            name="listar_provincias",
            description="Obtiene la lista completa de provincias de España desde la API oficial del Catastro",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="listar_municipios",
            description="Obtiene la lista de municipios de una provincia. Opcionalmente permite búsqueda parcial por nombre de municipio",
            inputSchema={
                "type": "object",
                "properties": {
                    "provincia": {
                        "type": "string",
                        "description": "Nombre de la provincia (ej: 'Granada', 'Madrid', 'Barcelona')"
                    },
                    "municipio_parcial": {
                        "type": "string",
                        "description": "Búsqueda parcial de municipio (opcional). Ej: 'B' encontrará 'BAZA', 'BENALUA', etc."
                    }
                },
                "required": ["provincia"]
            }
        ),
        types.Tool(
            name="listar_calles",
            description="Obtiene la lista de calles de un municipio específico",
            inputSchema={
                "type": "object",
                "properties": {
                    "provincia": {
                        "type": "string",
                        "description": "Nombre de la provincia"
                    },
                    "municipio": {
                        "type": "string",
                        "description": "Nombre del municipio"
                    }
                },
                "required": ["provincia", "municipio"]
            }
        ),
        types.Tool(
            name="convertir_coordenadas_a_referencia",
            description="Convierte coordenadas geográficas a referencia catastral",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitud": {
                        "type": "number",
                        "description": "Latitud en grados decimales"
                    },
                    "longitud": {
                        "type": "number",
                        "description": "Longitud en grados decimales"
                    },
                    "sistema_referencia": {
                        "type": "string",
                        "description": "Sistema de referencia (por defecto EPSG:4326)",
                        "default": "EPSG:4326"
                    }
                },
                "required": ["latitud", "longitud"]
            }
        ),
        types.Tool(
            name="convertir_referencia_a_coordenadas",
            description="Convierte referencia catastral a coordenadas geográficas",
            inputSchema={
                "type": "object",
                "properties": {
                    "referencia": {
                        "type": "string",
                        "description": "Referencia catastral (20 caracteres) o código de parcela (14 caracteres)"
                    },
                    "sistema_referencia": {
                        "type": "string",
                        "description": "Sistema de referencia (por defecto EPSG:4326)",
                        "default": "EPSG:4326"
                    }
                },
                "required": ["referencia"]
            }
        ),
        types.Tool(
            name="geocodificar_direccion",
            description="Convierte una dirección en texto a coordenadas y referencia catastral usando CartoCiudad",
            inputSchema={
                "type": "object",
                "properties": {
                    "direccion": {
                        "type": "string",
                        "description": "Dirección a geocodificar (ej: 'Calle Gran Vía 1')"
                    },
                    "municipio": {
                        "type": "string",
                        "description": "Municipio de la dirección (opcional pero recomendado)"
                    }
                },
                "required": ["direccion"]
            }
        ),
        types.Tool(
            name="obtener_geometria_parcela",
            description="Obtiene la geometría completa de una parcela (polígono, centroide, superficie) usando servicios WFS del Catastro",
            inputSchema={
                "type": "object",
                "properties": {
                    "referencia": {
                        "type": "string",
                        "description": "Referencia catastral de la parcela (20 caracteres)"
                    },
                    "sistema_referencia": {
                        "type": "string",
                        "description": "Sistema de referencia espacial (por defecto EPSG:4326)",
                        "default": "EPSG:4326"
                    }
                },
                "required": ["referencia"]
            }
        ),
        types.Tool(
            name="consultar_metaparcela",
            description="Consulta una MetaParcela (parcela con múltiples referencias catastrales) por referencia o por componentes (provincia, municipio, polígono, parcela)",
            inputSchema={
                "type": "object",
                "properties": {
                    "referencia": {
                        "type": "string",
                        "description": "Referencia catastral base de la MetaParcela (opcional)"
                    },
                    "provincia": {
                        "type": "string",
                        "description": "Nombre de la provincia (opcional)"
                    },
                    "municipio": {
                        "type": "string",
                        "description": "Nombre del municipio (opcional)"
                    },
                    "poligono": {
                        "type": "integer",
                        "description": "Número del polígono (opcional)"
                    },
                    "parcela": {
                        "type": "integer",
                        "description": "Número de la parcela (opcional)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="exportar_geometria_geojson",
            description="Exporta la geometría de una parcela en formato GeoJSON estándar para uso en aplicaciones de mapas",
            inputSchema={
                "type": "object",
                "properties": {
                    "referencia": {
                        "type": "string",
                        "description": "Referencia catastral de la parcela (20 caracteres)"
                    }
                },
                "required": ["referencia"]
            }
        )
    ]
    
    logger.info(f"✅ Herramientas MCP definidas: {len(tools)}")
    return tools

@app.call_tool()
async def handle_call_tool(
    name: str, arguments: Optional[Dict[str, Any]]
) -> List[types.TextContent]:
    """Maneja las llamadas a las herramientas"""
    logger.info(f"🔧 Ejecutando herramienta: {name} con argumentos: {arguments}")
    
    try:
        if arguments is None:
            arguments = {}
            
        if name == "consultar_catastro_por_referencia":
            referencia = arguments.get("referencia")
            if not referencia:
                raise ValueError("Referencia catastral requerida")
            
            resultado = await catastro_service.consultar_por_referencia(referencia)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado.model_dump(), indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "consultar_catastro_por_coordenadas":
            latitud = arguments.get("latitud")
            longitud = arguments.get("longitud")
            
            if latitud is None or longitud is None:
                raise ValueError("Latitud y longitud requeridas")
            
            resultado = await catastro_service.consultar_por_coordenadas(latitud, longitud)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado.model_dump(), indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "generar_resumen_ia":
            referencia = arguments.get("referencia")
            usar_openai = arguments.get("usar_openai", False)
            idioma = arguments.get("idioma", "es")
            
            if not referencia:
                raise ValueError("Referencia catastral requerida")
            
            resumen = await ai_service.generar_resumen(referencia, usar_openai, idioma)
            return [
                types.TextContent(
                    type="text",
                    text=resumen
                )
            ]
        
        elif name == "validar_referencia_catastral":
            referencia = arguments.get("referencia")
            if not referencia:
                raise ValueError("Referencia catastral requerida")
            
            # Usar el análisis detallado
            analisis = ReferenciaCatastral.analizar_referencia_detallado(referencia)
            
            # Mantener compatibilidad con la respuesta original
            resultado = {
                "referencia": referencia,
                "es_valida": analisis["es_referencia_completa"],
                "mensaje": analisis["mensaje"],
                "analisis_detallado": analisis
            }
            
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "buscar_catastro_por_direccion":
            direccion_completa = arguments.get("direccion_completa")
            
            if not direccion_completa:
                raise ValueError("Se requiere dirección completa en formato: 'TIPO_VIA NOMBRE_VIA NUMERO, CODIGO_POSTAL, MUNICIPIO, PROVINCIA'")
            
            # Parsear la dirección para extraer componentes
            componentes = parse_direccion_completa(direccion_completa)
            
            # Verificar si el parseado fue exitoso
            if "error" in componentes:
                error_response = {
                    "error": True,
                    "herramienta": "buscar_catastro_por_direccion",
                    "mensaje": componentes["error"],
                    "direccion_recibida": direccion_completa,
                    "formato_correcto": "TIPO_VIA NOMBRE_VIA NUMERO, CODIGO_POSTAL, MUNICIPIO, PROVINCIA",
                    "ejemplos": [
                        "CALLE REYES CATOLICOS 6, 18100, ARMILLA, GRANADA",
                        "AVENIDA CONSTITUCION 25, 14011, CORDOBA, CORDOBA"
                    ]
                }
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(error_response, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                    )
                ]
            
            resultado = await catastro_service.buscar_por_direccion(
                provincia=componentes.get("provincia", ""),
                municipio=componentes.get("municipio", ""),
                tipo_via=componentes.get("tipo_via", "CALLE"),
                nombre_via=componentes.get("nombre_via", ""),
                numero=componentes.get("numero", ""),
                direccion_original=direccion_completa
            )
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado.model_dump(), indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "consultar_parcela_por_codigo":
            codigo_parcela = arguments.get("codigo_parcela")
            
            if not codigo_parcela:
                raise ValueError("Código de parcela requerido")
            
            resultado = await catastro_service.consultar_parcela_por_codigo(codigo_parcela)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado.model_dump(), indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "listar_provincias":
            provincias = await catastro_service.listar_provincias()
            resultado = {
                "provincias": provincias,
                "total": len(provincias),
                "descripcion": "Lista completa de provincias de España desde la API oficial del Catastro"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "listar_municipios":
            provincia = arguments.get("provincia")
            municipio_parcial = arguments.get("municipio_parcial")
            
            if not provincia:
                raise ValueError("Provincia requerida")
            
            municipios = await catastro_service.listar_municipios(provincia, municipio_parcial)
            resultado = {
                "provincia": provincia,
                "municipio_parcial": municipio_parcial,
                "municipios": municipios,
                "total": len(municipios),
                "descripcion": f"Municipios encontrados en {provincia}" + (f" que contienen '{municipio_parcial}'" if municipio_parcial else "")
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "listar_calles":
            provincia = arguments.get("provincia")
            municipio = arguments.get("municipio")
            
            if not provincia or not municipio:
                raise ValueError("Provincia y municipio requeridos")
            
            calles = await catastro_service.listar_calles(provincia, municipio)
            resultado = {
                "provincia": provincia,
                "municipio": municipio,
                "calles": calles,
                "total": len(calles),
                "descripcion": f"Calles encontradas en {municipio}, {provincia}"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "convertir_coordenadas_a_referencia":
            latitud = arguments.get("latitud")
            longitud = arguments.get("longitud")
            srs = arguments.get("sistema_referencia", "EPSG:4326")
            
            if latitud is None or longitud is None:
                raise ValueError("Latitud y longitud requeridas")
            
            referencia = await catastro_service.convertir_coordenadas_a_rc(latitud, longitud, srs)
            resultado = {
                "coordenadas": {"latitud": latitud, "longitud": longitud},
                "sistema_referencia": srs,
                "referencia_catastral": referencia,
                "exito": referencia is not None,
                "descripcion": "Conversión de coordenadas a referencia catastral"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "convertir_referencia_a_coordenadas":
            referencia = arguments.get("referencia")
            srs = arguments.get("sistema_referencia", "EPSG:4326")
            
            if not referencia:
                raise ValueError("Referencia catastral requerida")
            
            coordenadas = await catastro_service.convertir_rc_a_coordenadas(referencia, srs)
            resultado = {
                "referencia_catastral": referencia,
                "sistema_referencia": srs,
                "coordenadas": coordenadas,
                "exito": coordenadas is not None,
                "descripcion": "Conversión de referencia catastral a coordenadas"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "geocodificar_direccion":
            direccion = arguments.get("direccion")
            municipio = arguments.get("municipio")
            
            if not direccion:
                raise ValueError("Dirección requerida")
            
            geocodificacion = await catastro_service.geocodificar_direccion(direccion, municipio)
            resultado = {
                "direccion": direccion,
                "municipio": municipio,
                "geocodificacion": geocodificacion,
                "exito": geocodificacion is not None,
                "descripcion": "Geocodificación usando CartoCiudad"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "obtener_geometria_parcela":
            referencia = arguments.get("referencia")
            srs = arguments.get("sistema_referencia", "EPSG:4326")
            
            if not referencia:
                raise ValueError("Referencia catastral requerida")
            
            geometria = await catastro_service.obtener_geometria_parcela(referencia, srs)
            resultado = {
                "referencia_catastral": referencia,
                "sistema_referencia": srs,
                "geometria": geometria,
                "exito": geometria is not None,
                "descripcion": "Geometría completa de la parcela obtenida desde servicios WFS del Catastro"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "consultar_metaparcela":
            referencia = arguments.get("referencia")
            provincia = arguments.get("provincia")
            municipio = arguments.get("municipio")
            poligono = arguments.get("poligono")
            parcela = arguments.get("parcela")
            
            metaparcela = await catastro_service.consultar_metaparcela(
                referencia=referencia,
                provincia=provincia,
                municipio=municipio,
                poligono=poligono,
                parcela=parcela
            )
            resultado = {
                "consulta": {
                    "referencia": referencia,
                    "provincia": provincia,
                    "municipio": municipio,
                    "poligono": poligono,
                    "parcela": parcela
                },
                "metaparcela": metaparcela,
                "exito": metaparcela is not None,
                "descripcion": "Consulta de MetaParcela (parcela con múltiples referencias catastrales)"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        elif name == "exportar_geometria_geojson":
            referencia = arguments.get("referencia")
            
            if not referencia:
                raise ValueError("Referencia catastral requerida")
            
            geojson = await catastro_service.exportar_geometria_geojson(referencia)
            resultado = {
                "referencia_catastral": referencia,
                "geojson": geojson,
                "exito": geojson is not None,
                "descripcion": "Geometría de la parcela exportada en formato GeoJSON estándar"
            }
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(resultado, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                )
            ]
        
        else:
            raise ValueError(f"Herramienta desconocida: {name}")
    
    except Exception as e:
        logger.error(f"❌ Error en herramienta {name}: {str(e)}")
        error_response = {
            "error": True,
            "herramienta": name,
            "mensaje": str(e),
            "argumentos": arguments
        }
        return [
            types.TextContent(
                type="text",
                text=json.dumps(error_response, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
            )
        ]

@app.list_resources()
async def handle_list_resources() -> List[types.Resource]:
    """Lista los recursos disponibles"""
    return [
        types.Resource(
            uri="catastro://api/info",
            name="Información de la API del Catastro",
            description="Información sobre endpoints y capacidades de la API",
            mimeType="application/json"
        )
    ]

@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Maneja la lectura de recursos"""
    logger.info(f"📖 Leyendo recurso: {uri}")
    
    if uri == "catastro://api/info":
        try:
            resource_info = {
                "version": "1.0.0",
                "description": "Servidor MCP para consultas al Catastro de España",
                "herramientas_disponibles": [
                    "consultar_catastro_por_referencia - ✅ Consulta por referencia catastral (FUNCIONAL)",
                    "consultar_catastro_por_coordenadas - ✅ Consulta por coordenadas GPS (FUNCIONAL)",
                    "buscar_catastro_por_direccion - ⚠️ INFORMATIVA: Limitaciones API y alternativas",
                    "generar_resumen_ia - ✅ Genera resumen con IA (FUNCIONAL)",
                    "validar_referencia_catastral - ✅ Analiza referencias completas y parciales (FUNCIONAL)",
                    "consultar_parcela_por_codigo - ✅ Consulta parcelas con división horizontal (FUNCIONAL)",
                    "listar_provincias - ✅ Lista todas las provincias de España (NUEVO)",
                    "listar_municipios - ✅ Lista municipios por provincia con búsqueda parcial (NUEVO)",
                    "listar_calles - ✅ Lista calles de un municipio (NUEVO)",
                    "convertir_coordenadas_a_referencia - ✅ Coordenadas → Referencia catastral (NUEVO)",
                    "convertir_referencia_a_coordenadas - ✅ Referencia catastral → Coordenadas (NUEVO)",
                    "geocodificar_direccion - ✅ Dirección → Coordenadas + RC usando CartoCiudad (NUEVO)"
                ],
                "importante": "Servidor mejorado con funcionalidades avanzadas. Nuevas herramientas de geocodificación y listados disponibles.",
                "ejemplos_funcionales": {
                    "referencia_completa": "4228928VG4141K0001IZ",
                    "referencia_parcial": "2314501EG1421S", 
                    "coordenadas": "40.4168, -3.7038"
                },
                "formato_direccion_requerido": "TIPO_VIA NOMBRE_VIA NUMERO, CODIGO_POSTAL, MUNICIPIO, PROVINCIA"
            }
            result = json.dumps(resource_info, indent=2, ensure_ascii=False)
            logger.info(f"✅ Recurso api/info devuelto exitosamente")
            return result
        except Exception as e:
            logger.error(f"❌ Error cargando recurso api/info: {e}")
            import traceback
            traceback.print_exc()
            return json.dumps({"error": f"Error interno: {str(e)}"}, ensure_ascii=False)
    else:
        logger.warning(f"⚠️ Recurso solicitado no existe: {uri}")
        return json.dumps({"error": f"Recurso no encontrado: {uri}"}, ensure_ascii=False)

async def main():
    """Función principal para ejecutar el servidor MCP"""
    logger.info("🚀 Iniciando servidor MCP Catastro REAL para Claude Code...")
    
    # Ejecutar servidor con stdio (protocolo MCP real)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="catastro-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Servidor MCP detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal en servidor MCP: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)