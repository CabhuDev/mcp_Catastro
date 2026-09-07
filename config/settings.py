"""
Configuración del servicio MCP Catastro
"""

import logging
import os
import sys
from typing import TextIO

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """Interpreta una variable de entorno booleana de forma predecible."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Configuración de la aplicación"""

    def __init__(self):
        # Configuración del servicio
        self.app_name = os.getenv("CATASTRO_APP_NAME", "MCP Catastro España")
        self.app_version = os.getenv("CATASTRO_APP_VERSION", "2.0.0")
        self.debug = _env_bool("CATASTRO_DEBUG")

        # API del Catastro
        self.catastro_base_url = os.getenv(
            "CATASTRO_CATASTRO_BASE_URL", "https://ovc.catastro.meh.es"
        )
        self.catastro_timeout = int(os.getenv("CATASTRO_CATASTRO_TIMEOUT", "30"))
        self.catastro_max_retries = int(os.getenv("CATASTRO_CATASTRO_MAX_RETRIES", "3"))
        self.catastro_retry_delay = float(os.getenv("CATASTRO_CATASTRO_RETRY_DELAY", "1.0"))

        self.catastro_total_timeout = float(os.getenv("CATASTRO_TOTAL_TIMEOUT", "30"))
        self.catastro_max_concurrency = int(os.getenv("CATASTRO_MAX_CONCURRENCY", "4"))
        self.catastro_cache_ttl = float(os.getenv("CATASTRO_CACHE_TTL", "60"))
        self.catastro_catalogue_cache_ttl = float(os.getenv("CATASTRO_CATALOGUE_CACHE_TTL", "3600"))
        self.catastro_cache_size = int(os.getenv("CATASTRO_CACHE_SIZE", "128"))
        self.revision = os.getenv("CATASTRO_REVISION", "desconocida")
        if (
            min(self.catastro_timeout, self.catastro_total_timeout, self.catastro_max_concurrency)
            <= 0
        ):
            raise ValueError("Timeouts y concurrencia deben ser positivos")
        if (
            min(
                self.catastro_max_retries,
                self.catastro_retry_delay,
                self.catastro_cache_ttl,
                self.catastro_catalogue_cache_ttl,
                self.catastro_cache_size,
            )
            < 0
        ):
            raise ValueError("Reintentos y caché no pueden ser negativos")

        # OpenAI (opcional)
        self.openai_api_key = os.getenv("CATASTRO_OPENAI_API_KEY")
        self.openai_model = os.getenv("CATASTRO_OPENAI_MODEL", "gpt-4")
        self.openai_max_tokens = int(os.getenv("CATASTRO_OPENAI_MAX_TOKENS", "500"))
        self.openai_temperature = float(os.getenv("CATASTRO_OPENAI_TEMPERATURE", "0.3"))

        # Logging
        default_log_level = "DEBUG" if self.debug else "INFO"
        self.log_level = os.getenv("CATASTRO_LOG_LEVEL", default_log_level).upper()
        self.log_format = os.getenv(
            "CATASTRO_LOG_FORMAT",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.log_sensitive_data = _env_bool("CATASTRO_LOG_SENSITIVE_DATA")

        # Paths de documentación
        self.docs_path = os.getenv("CATASTRO_DOCS_PATH", "/docs")
        self.redoc_path = os.getenv("CATASTRO_REDOC_PATH", "/redoc")


# Configuración específica de endpoints del Catastro
class CatastroEndpoints:
    """URLs de los servicios web del Catastro - API WCF Oficial"""

    # Base paths para servicios WCF
    CALLEJERO_BASE = "/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc"
    CALLEJERO_CODIGOS_BASE = "/OVCServWeb/OVCWcfCallejero/COVCCallejeroCodigos.svc"
    COORDENADAS_BASE = "/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc"

    # Consultas por denominación (REST JSON)
    CONSULTA_PROVINCIA = f"{CALLEJERO_BASE}/json/ObtenerProvincias"
    CONSULTA_MUNICIPIO = f"{CALLEJERO_BASE}/json/ObtenerMunicipios"
    CONSULTA_VIA = f"{CALLEJERO_BASE}/json/ObtenerCallejero"
    CONSULTA_NUMERO = f"{CALLEJERO_BASE}/json/ObtenerNumerero"
    CONSULTA_DNPLOC = f"{CALLEJERO_BASE}/json/Consulta_DNPLOC"
    CONSULTA_DNPRC = f"{CALLEJERO_BASE}/json/Consulta_DNPRC"
    CONSULTA_DNPPP = f"{CALLEJERO_BASE}/json/Consulta_DNPPP"

    # Consultas por códigos (REST JSON)
    CONSULTA_MUNICIPIO_CODIGOS = f"{CALLEJERO_CODIGOS_BASE}/json/ConsultaMunicipioCodigos"
    CONSULTA_VIA_CODIGOS = f"{CALLEJERO_CODIGOS_BASE}/json/ConsultaViaCodigos"
    CONSULTA_NUMERO_CODIGOS = f"{CALLEJERO_CODIGOS_BASE}/json/ConsultaNumeroCodigos"
    CONSULTA_DNPLOC_CODIGOS = f"{CALLEJERO_CODIGOS_BASE}/json/Consulta_DNPLOC_Codigos"
    CONSULTA_DNPRC_CODIGOS = f"{CALLEJERO_CODIGOS_BASE}/json/Consulta_DNPRC_Codigos"
    CONSULTA_DNPPP_CODIGOS = f"{CALLEJERO_CODIGOS_BASE}/json/Consulta_DNPPP_Codigos"

    # Servicios de coordenadas (REST JSON)
    CONSULTA_RCCOOR = f"{COORDENADAS_BASE}/json/Consulta_RCCOOR"
    CONSULTA_RCCOOR_DISTANCIA = f"{COORDENADAS_BASE}/json/Consulta_RCCOOR_Distancia"
    CONSULTA_CPMRC = f"{COORDENADAS_BASE}/json/Consulta_CPMRC"

    # Consulta por referencia catastral (principal)
    CONSULTA_DNP = CONSULTA_DNPRC

    # Aliases para compatibilidad
    CONSULTA_COORDENADAS = CONSULTA_RCCOOR  # Por coordenadas
    CONSULTA_MUNICIPIOS = CONSULTA_MUNICIPIO  # Municipios
    CONSULTA_PROVINCIAS = CONSULTA_PROVINCIA  # Provincias

    # URLs de ayuda para desarrollo
    HELP_CALLEJERO = f"{CALLEJERO_BASE}/json/help"
    HELP_CODIGOS = f"{CALLEJERO_CODIGOS_BASE}/json/help"
    HELP_COORDENADAS = f"{COORDENADAS_BASE}/json/help"


def get_settings() -> Settings:
    """Obtiene la configuración de la aplicación"""
    return Settings()


def configure_logging(
    settings: Settings | None = None,
    *,
    stream: TextIO | None = None,
    force: bool = True,
) -> None:
    """Configura logs operativos en stderr sin interferir con MCP por stdout."""
    current = settings or get_settings()
    level = getattr(logging, current.log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format=current.log_format,
        stream=stream or sys.stderr,
        force=force,
    )

    # MCP, HTTPX y OpenAI pueden registrar mensajes o URLs con argumentos. Se
    # silencian salvo que coincidan los dos controles del opt-in sensible.
    allow_sensitive = current.log_sensitive_data and level <= logging.DEBUG
    third_party_level = level if allow_sensitive else logging.WARNING
    for logger_name in ("mcp", "httpx", "httpcore", "openai"):
        logging.getLogger(logger_name).setLevel(third_party_level)


def log_sensitive(
    logger: logging.Logger,
    enabled: bool,
    message: str,
    *args: object,
) -> None:
    """Registra datos sensibles solo con opt-in y nivel DEBUG efectivo."""
    if enabled and logger.isEnabledFor(logging.DEBUG):
        logger.debug(message, *args)


def log_failure(
    logger: logging.Logger,
    level: int,
    enabled: bool,
    operation: str,
    error: BaseException,
) -> None:
    """Registra un fallo sin incluir el mensaje potencialmente sensible."""
    logger.log(level, "%s (%s)", operation, type(error).__name__)
    log_sensitive(logger, enabled, "Detalle sensible del fallo: %r", error)


# Configuración de validación
VALIDATION_CONFIG = {
    "referencia_catastral": {
        "pattern": r"^[0-9]{7}[A-Z]{2}[0-9]{4}[A-Z]{1}[0-9]{4}[A-Z]{2}$",
        "length": 20,
    },
    "coordenadas": {
        "latitud_min": -90.0,
        "latitud_max": 90.0,
        "longitud_min": -180.0,
        "longitud_max": 180.0,
    },
}


# Mensajes de error estándar
ERROR_MESSAGES = {
    "REFERENCIA_INVALIDA": "El formato de la referencia catastral no es válido",
    "COORDENADAS_INVALIDAS": "Las coordenadas están fuera del rango válido para España",
    "SERVICIO_NO_DISPONIBLE": "El servicio del Catastro no está disponible temporalmente",
    "DATOS_NO_ENCONTRADOS": "No se encontraron datos para la consulta realizada",
    "ERROR_CONEXION": "Error de conexión con el servicio del Catastro",
    "TIMEOUT": "La consulta ha excedido el tiempo límite",
    "API_KEY_INVALIDA": "La clave de API de OpenAI no es válida o ha caducado",
}
