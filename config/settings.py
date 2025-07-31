"""
Configuración del servicio MCP Catastro
"""

import os
from typing import Optional


class Settings:
    """Configuración de la aplicación"""
    
    def __init__(self):
        # Configuración del servicio
        self.app_name = os.getenv("CATASTRO_APP_NAME", "MCP Catastro España")
        self.app_version = os.getenv("CATASTRO_APP_VERSION", "1.0.0")
        self.debug = os.getenv("CATASTRO_DEBUG", "false").lower() == "true"
        
        # API del Catastro (URLs base oficiales)
        self.catastro_base_url = os.getenv("CATASTRO_CATASTRO_BASE_URL", "https://ovc.catastro.meh.es")
        self.catastro_base_url_callejero = os.getenv("CATASTRO_CALLEJERO_URL", "https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/json")
        self.catastro_base_url_coordenadas = os.getenv("CATASTRO_COORDENADAS_URL", "https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json")
        self.catastro_base_url_geografia = os.getenv("CATASTRO_GEOGRAFIA_URL", "http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx")
        self.catastro_base_url_croquis = os.getenv("CATASTRO_CROQUIS_URL", "https://www1.sedecatastro.gob.es/CYCBienInmueble/SECImprimirCroquisYDatos.aspx")
        self.cartociudad_base_url = os.getenv("CARTOCIUDAD_BASE_URL", "https://www.cartociudad.es/geocoder/api/geocoder")
        self.catastro_timeout = int(os.getenv("CATASTRO_CATASTRO_TIMEOUT", "30"))
        self.catastro_max_retries = int(os.getenv("CATASTRO_CATASTRO_MAX_RETRIES", "3"))
        self.catastro_retry_delay = float(os.getenv("CATASTRO_CATASTRO_RETRY_DELAY", "1.0"))
        
        # Rate limiting
        self.max_requests_per_minute = int(os.getenv("CATASTRO_MAX_REQUESTS_PER_MINUTE", "60"))
        self.max_requests_per_hour = int(os.getenv("CATASTRO_MAX_REQUESTS_PER_HOUR", "1000"))
        
        # OpenAI (opcional)
        self.openai_api_key = os.getenv("CATASTRO_OPENAI_API_KEY")
        self.openai_model = os.getenv("CATASTRO_OPENAI_MODEL", "gpt-4")
        self.openai_max_tokens = int(os.getenv("CATASTRO_OPENAI_MAX_TOKENS", "500"))
        self.openai_temperature = float(os.getenv("CATASTRO_OPENAI_TEMPERATURE", "0.3"))
        
        # Logging
        self.log_level = os.getenv("CATASTRO_LOG_LEVEL", "INFO")
        self.log_format = os.getenv("CATASTRO_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # Cache (opcional)
        self.enable_cache = os.getenv("CATASTRO_ENABLE_CACHE", "true").lower() == "true"
        self.cache_ttl_seconds = int(os.getenv("CATASTRO_CACHE_TTL_SECONDS", "3600"))
        self.cache_max_size = int(os.getenv("CATASTRO_CACHE_MAX_SIZE", "1000"))
        
        # Métricas
        self.enable_metrics = os.getenv("CATASTRO_ENABLE_METRICS", "true").lower() == "true"
        self.metrics_port = int(os.getenv("CATASTRO_METRICS_PORT", "9090"))
        
        # Paths de documentación
        self.docs_path = os.getenv("CATASTRO_DOCS_PATH", "/docs")
        self.redoc_path = os.getenv("CATASTRO_REDOC_PATH", "/redoc")


# Configuración específica de endpoints del Catastro
class CatastroEndpoints:
    """URLs de los servicios web del Catastro - API oficial mejorada"""
    
    # Base URLs (API oficial del Catastro)
    CALLEJERO_BASE = "/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc"
    COORDENADAS_BASE = "/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc"
    GEOGRAFIA_BASE = "http://ovc.catastro.meh.es/INSPIRE/wfsCP.aspx"  # Para geometrías
    CROQUIS_BASE = "https://www1.sedecatastro.gob.es/CYCBienInmueble/SECImprimirCroquisYDatos.aspx"
    CARTOCIUDAD_BASE = "https://www.cartociudad.es/geocoder/api/geocoder"
    
    # Consultas principales (JSON)
    CONSULTA_DNPRC = f"{CALLEJERO_BASE}/json/Consulta_DNPRC"  # Por referencia catastral
    CONSULTA_DNPPP = f"{CALLEJERO_BASE}/json/Consulta_DNPPP"  # Por polígono/parcela
    CONSULTA_DNPLOC = f"{CALLEJERO_BASE}/json/Consulta_DNPLOC"  # Por dirección
    CONSULTA_RCCOOR = f"{COORDENADAS_BASE}/json/Consulta_RCCOOR"  # Coordenadas -> RC
    CONSULTA_CPMRC = f"{COORDENADAS_BASE}/json/Consulta_CPMRC"  # RC -> Coordenadas
    
    # Consultas auxiliares (API oficial)
    OBTENER_PROVINCIAS = f"{CALLEJERO_BASE}/json/ObtenerProvincias"
    OBTENER_MUNICIPIOS = f"{CALLEJERO_BASE}/json/ObtenerMunicipios"
    OBTENER_CALLEJERO = f"{CALLEJERO_BASE}/json/ObtenerCallejero"
    
    # Servicios WFS para geometrías
    WFS_GETPARCEL = f"{GEOGRAFIA_BASE}?service=wfs&version=2&request=getfeature&STOREDQUERIE_ID=GetParcel"
    
    # CartoCiudad para geocodificación
    CARTOCIUDAD_GEOCODER = f"{CARTOCIUDAD_BASE}/findJsonp"
    
    # Aliases principales
    CONSULTA_DNP = CONSULTA_DNPRC
    CONSULTA_COORDENADAS = CONSULTA_RCCOOR
    CONSULTA_MUNICIPIOS = OBTENER_MUNICIPIOS
    CONSULTA_PROVINCIAS = OBTENER_PROVINCIAS


# Configuración de logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
        }
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "level": "DEBUG",
            "formatter": "detailed",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/catastro_mcp.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
            "propagate": False
        }
    }
}


def get_settings() -> Settings:
    """Obtiene la configuración de la aplicación"""
    return Settings()


# Configuración de validación (mejorada)
VALIDATION_CONFIG = {
    "referencia_catastral_completa": {
        "pattern": r"^[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]{1}[0-9]{4}[A-Z]{2}$",
        "length": 20,
        "description": "Referencia catastral completa de 20 caracteres"
    },
    "referencia_catastral_parcial": {
        "pattern": r"^[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]{1}$",
        "length": 14,
        "description": "Código de parcela de 14 caracteres"
    },
    "coordenadas": {
        "latitud_min": 35.0,
        "latitud_max": 44.0,
        "longitud_min": -10.0,
        "longitud_max": 5.0
    },
    "provincia": {
        "min_length": 2,
        "max_length": 50
    },
    "municipio": {
        "min_length": 2,
        "max_length": 100
    }
}

# Funciones auxiliares de validación
def normalizar_provincia(provincia: str) -> str:
    """Normaliza el nombre de una provincia usando el mapeo oficial"""
    if not provincia:
        return ""
    
    provincia_capitalizada = provincia.capitalize()
    return MAPEOS_PROVINCIAS.get(provincia_capitalizada, provincia.upper())

def obtener_codigo_tipo_via(sigla: str) -> str:
    """Obtiene la descripción completa de un tipo de vía"""
    return TIPOS_VIA.get(sigla.upper(), sigla)

def validar_sistema_referencia(srs: str) -> bool:
    """Valida si un sistema de referencia es soportado"""
    return srs in SISTEMAS_REFERENCIA


# Mapeo de provincias alternativas
MAPEOS_PROVINCIAS = {
    'La Coruña': 'A Coruña',
    'Orense': 'Ourense',
    'Santa Cruz De Tenerife': 'S.C. Tenerife',
    'Las Palmas De Gran Canaria': 'Las Palmas',
    'Alicante': 'Alacant',
    'Almería': 'Almeria',
    'Cádiz': 'Cadiz',
    'Córdoba': 'Cordoba',
    'Gerona': 'Girona',
    'Castellón De La Plana': 'Castello',
    'Castellón': 'Castello',
    'Lérida': 'Lleida',
    'Málaga': 'Malaga',
    'León': 'Leon',
    'Ávila': 'Avila',
    'Cáceres': 'Caceres',
    'Baleares': 'Illes Balears',
    'Islas Baleares': 'Illes Balears',
    'Jaén': 'Jaen',
    'València': 'Valencia'
}

# Tipos de vía completos (API oficial)
TIPOS_VIA = {
    "AC": "ACCESO", "AG": "AGREGADO", "AL": "ALDEA, ALAMEDA", "AN": "ANDADOR", 
    "AR": "AREA, ARRABAL", "AU": "AUTOPISTA", "AV": "AVENIDA", "AY": "ARROYO",
    "BJ": "BAJADA", "BL": "BLOQUE", "BO": "BARRIO", "BQ": "BARRANQUIL", 
    "BR": "BARRANCO", "CA": "CAÑADA", "CG": "COLEGIO, CIGARRAL", "CH": "CHALET",
    "CI": "CINTURON", "CJ": "CALLEJA, CALLEJON", "CL": "CALLE", "CM": "CAMINO, CARMEN",
    "CN": "COLONIA", "CO": "CONCEJO, COLEGIO", "CP": "CAMPA, CAMPO", "CR": "CARRETERA, CARRERA",
    "CS": "CASERIO", "CT": "CUESTA, COSTANILLA", "CU": "CONJUNTO", "CY": "CALEYA",
    "CZ": "CALLIZO", "DE": "DETRAS", "DP": "DIPUTACION", "DS": "DISEMINADOS",
    "ED": "EDIFICIOS", "EM": "EXTRAMUROS", "EN": "ENTRADA, ENSANCHE", "EP": "ESPALDA",
    "ER": "EXTRARRADIO", "ES": "ESCALINATA", "EX": "EXPLANADA", "FC": "FERROCARRIL",
    "FN": "FINCA", "GL": "GLORIETA", "GR": "GRUPO", "GV": "GRAN VIA",
    "HT": "HUERTA, HUERTO", "JR": "JARDINES", "LA": "LAGO", "LD": "LADO, LADERA",
    "LG": "LUGAR", "MA": "MALECON", "MC": "MERCADO", "ML": "MUELLE",
    "MN": "MUNICIPIO", "MS": "MASIAS", "MT": "MONTE", "MZ": "MANZANA",
    "PB": "POBLADO", "PC": "PLACETA", "PD": "PARTIDA", "PI": "PARTICULAR",
    "PJ": "PASAJE, PASADIZO", "PL": "POLIGONO", "PM": "PARAMO", "PQ": "PARROQUIA, PARQUE",
    "PR": "PROLONGACION, CONTINUAC.", "PS": "PASEO", "PT": "PUENTE", "PU": "PASADIZO",
    "PZ": "PLAZA", "QT": "QUINTA", "RA": "RACONADA", "RB": "RAMBLA",
    "RC": "RINCON, RINCONA", "RD": "RONDA", "RM": "RAMAL", "RP": "RAMPA",
    "RR": "RIERA", "RU": "RUA", "SA": "SALIDA", "SC": "SECTOR",
    "SD": "SENDA", "SL": "SOLAR", "SN": "SALON", "SU": "SUBIDA",
    "TN": "TERRENOS", "TO": "TORRENTE", "TR": "TRAVESIA", "UR": "URBANIZACION",
    "VA": "VALLE", "VD": "VIADUCTO", "VI": "VIA", "VL": "VIAL", "VR": "VEREDA"
}

# Sistemas de referencia soportados
SISTEMAS_REFERENCIA = {
    'EPSG:4230': 'Geográficas en ED 50',
    'EPSG:4326': 'Geográficas en WGS 80',
    'EPSG:4258': 'Geográficas en ETRS89',
    'EPSG:32627': 'UTM huso 27N en WGS 84',
    'EPSG:32628': 'UTM huso 28N en WGS 84',
    'EPSG:32629': 'UTM huso 29N en WGS 84',
    'EPSG:32630': 'UTM huso 30N en WGS 84',
    'EPSG:32631': 'UTM huso 31N en WGS 84',
    'EPSG:25829': 'UTM huso 29N en ETRS89',
    'EPSG:25830': 'UTM huso 30N en ETRS89',
    'EPSG:25831': 'UTM huso 31N en ETRS89',
    'EPSG:23029': 'UTM huso 29N en ED50',
    'EPSG:23030': 'UTM huso 30N en ED50',
    'EPSG:23031': 'UTM huso 31N en ED50'
}

# Mensajes de error estándar (mejorados)
ERROR_MESSAGES = {
    "REFERENCIA_INVALIDA": "El formato de la referencia catastral no es válido",
    "COORDENADAS_INVALIDAS": "Las coordenadas están fuera del rango válido para España",
    "SERVICIO_NO_DISPONIBLE": "El servicio del Catastro no está disponible temporalmente",
    "LIMITE_VELOCIDAD": "Se ha excedido el límite de consultas por minuto",
    "DATOS_NO_ENCONTRADOS": "No se encontraron datos para la consulta realizada",
    "ERROR_CONEXION": "Error de conexión con el servicio del Catastro",
    "TIMEOUT": "La consulta ha excedido el tiempo límite",
    "API_KEY_INVALIDA": "La clave de API de OpenAI no es válida o ha caducado",
    "NO_HAY_COINCIDENCIAS": "NO HAY COINCIDENCIAS EN LA BÚSQUEDA DE VÍAS",
    "MULTIPLE_REFERENCIAS": "Esta parcela tiene varias referencias catastrales. Usa un objeto MetaParcela.",
    "RESPUESTA_VACIA": "El servidor ha devuelto una respuesta vacía"
}
