#!/usr/bin/env python3
"""Servidor MCP v2 para consultar el Catastro de España."""

import logging
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any, Literal

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from config.settings import configure_logging, get_settings
from models.catastro_models import CatastroResponse, ReferenciaCatastral, ResumenIA
from services.ai_summary import AIService
from services.catastro_service import CatastroService

logger = logging.getLogger(__name__)

settings = get_settings()


@dataclass(frozen=True)
class AppContext:
    """Recursos compartidos durante la vida del servidor MCP."""

    catastro_service: CatastroService
    ai_service: AIService


@asynccontextmanager
async def app_lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    """Crea una única conexión HTTP reutilizable y garantiza su cierre."""
    async with httpx.AsyncClient(timeout=settings.catastro_timeout) as http_client:
        catastro_service = CatastroService(http_client=http_client)
        ai_service = AIService(catastro_service=catastro_service)
        try:
            yield AppContext(catastro_service=catastro_service, ai_service=ai_service)
        finally:
            await ai_service.aclose()


EXTERNAL_READ_ONLY_TOOL = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=True,
)
LOCAL_READ_ONLY_TOOL = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

app = MCPServer(
    "catastro-mcp",
    title="Catastro de España",
    description="Consultas de datos públicos del Catastro de España.",
    instructions=(
        "Consulta datos públicos por referencia, parcela, dirección o coordenadas. "
        "Las búsquedas pueden devolver varios candidatos: solicita escalera, planta o puerta "
        "para elegir un inmueble. Comprueba estado_consulta y codigo_error; sin_datos no "
        "equivale a un fallo de servicio. La cobertura depende de la Dirección General del Catastro."
    ),
    version=settings.app_version,
    lifespan=app_lifespan,
)


def parse_direccion_completa(direccion: str) -> dict[str, Any]:
    """Adaptador de texto libre; los campos explícitos son preferibles."""
    parts = [p.strip() for p in direccion.split(",")]
    if len(parts) not in (3, 4):
        return {"error": "Use 'VÍA NÚMERO, MUNICIPIO, PROVINCIA' o añada el CP tras la vía"}
    road = parts[0]
    types = (
        r"CALLE|AVENIDA|PLAZA|PASEO|CARRETERA|CAMINO|TRAVES[IÍ]A|GLORIETA|CL|AV|PZ|PS|CR|CM|TR|GL"
    )
    match = re.match(rf"^({types})\.?\s+(.+)$", road, re.IGNORECASE)
    kind, name = (match[1], match[2]) if match else ("", road)
    number_match = re.search(r"\s+(S/N|[0-9]+(?:\s*BIS|[A-Z]|[-/][0-9]+)?)$", name, re.IGNORECASE)
    number = number_match[1] if number_match else ""
    if number_match:
        name = name[: number_match.start()].strip()
    return {
        "tipo_via": kind,
        "nombre_via": name,
        "numero": number,
        "municipio": parts[-2],
        "provincia": parts[-1],
        "codigo_postal": parts[1] if len(parts) == 4 else "",
    }


@app.tool(title="Consultar inmueble por referencia", annotations=EXTERNAL_READ_ONLY_TOOL)
async def consultar_catastro_por_referencia(
    ctx: Context[AppContext],
    referencia: Annotated[
        str,
        Field(
            min_length=1,
            max_length=64,
            description="Referencia catastral completa de 20 caracteres alfanuméricos.",
        ),
    ],
    incluir_raw: Annotated[
        bool, Field(description="Incluir respuesta original para diagnóstico")
    ] = False,
) -> CatastroResponse:
    """Consulta los datos de un inmueble por su referencia catastral completa."""
    resultado = (
        await ctx.request_context.lifespan_context.catastro_service.consultar_por_referencia(
            referencia, incluir_raw
        )
    )
    return resultado


@app.tool(title="Localizar parcelas por coordenadas", annotations=EXTERNAL_READ_ONLY_TOOL)
async def consultar_catastro_por_coordenadas(
    ctx: Context[AppContext],
    latitud: Annotated[
        float, Field(ge=-90.0, le=90.0, description="Latitud WGS84 en grados decimales.")
    ],
    longitud: Annotated[
        float,
        Field(ge=-180.0, le=180.0, description="Longitud WGS84 en grados decimales."),
    ],
    incluir_raw: Annotated[
        bool, Field(description="Incluir respuesta original para diagnóstico")
    ] = False,
) -> CatastroResponse:
    """Localiza parcelas por coordenadas y devuelve sus inmuebles como candidatos."""
    resultado = (
        await ctx.request_context.lifespan_context.catastro_service.consultar_por_coordenadas(
            latitud, longitud, incluir_raw
        )
    )
    return resultado


@app.tool(title="Generar resumen catastral", annotations=EXTERNAL_READ_ONLY_TOOL)
async def generar_resumen_ia(
    ctx: Context[AppContext],
    referencia: Annotated[
        str,
        Field(
            min_length=1,
            max_length=64,
            description="Referencia catastral completa de 20 caracteres.",
        ),
    ],
    usar_openai: Annotated[
        bool, Field(description="Usar OpenAI si existe una clave configurada.")
    ] = False,
    idioma: Annotated[
        Literal["es", "en", "ca"],
        Field(description="Idioma del resumen: español, inglés o catalán."),
    ] = "es",
) -> ResumenIA:
    """Resume datos y declara el método usado y cualquier degradación a plantilla."""
    return await ctx.request_context.lifespan_context.ai_service.generar_resumen(
        referencia, usar_openai, idioma
    )


@app.tool(title="Validar referencia catastral", annotations=LOCAL_READ_ONLY_TOOL)
def validar_referencia_catastral(
    referencia: Annotated[
        str,
        Field(
            min_length=1,
            description="Referencia completa de 20 caracteres o código de parcela de 14.",
        ),
    ],
) -> dict[str, Any]:
    """Valida y explica referencias catastrales completas y parciales."""
    analisis = ReferenciaCatastral.analizar_referencia_detallado(referencia)
    return {
        "referencia": referencia,
        "es_valida": analisis["es_valida"],
        "mensaje": analisis["mensaje"],
        "analisis_detallado": analisis,
    }


@app.tool(title="Buscar inmuebles por dirección", annotations=EXTERNAL_READ_ONLY_TOOL)
async def buscar_catastro_por_direccion(
    ctx: Context[AppContext],
    direccion_completa: Annotated[
        str, Field(description="Texto opcional: VÍA NÚMERO, CP, MUNICIPIO, PROVINCIA")
    ] = "",
    provincia: str = "",
    municipio: str = "",
    tipo_via: str = "",
    nombre_via: str = "",
    numero: str = "",
    bloque: str = "",
    escalera: str = "",
    planta: str = "",
    puerta: str = "",
    incluir_raw: bool = False,
) -> CatastroResponse:
    """Busca por campos estructurados o texto; los campos explícitos prevalecen.

    Devuelve candidatos cuando falta número o hay nombres ambiguos. En edificios
    devuelve los inmuebles para seleccionar escalera/planta/puerta sin adivinar.
    """
    fields = {
        "provincia": provincia,
        "municipio": municipio,
        "tipo_via": tipo_via,
        "nombre_via": nombre_via,
        "numero": numero,
    }
    if direccion_completa:
        parsed = parse_direccion_completa(direccion_completa)
        if "error" in parsed:
            return CatastroResponse(
                referencia_catastral="BUSQUEDA_DIRECCION",
                estado_consulta="error_formato",
                codigo_error="ENTRADA_INVALIDA",
                mensaje_error=parsed["error"],
            )
        fields = {key: value or parsed[key] for key, value in fields.items()}
    return await ctx.request_context.lifespan_context.catastro_service.buscar_por_direccion(
        **fields,
        bloque=bloque,
        escalera=escalera,
        planta=planta,
        puerta=puerta,
        incluir_raw=incluir_raw,
    )


@app.tool(title="Consultar parcela", annotations=EXTERNAL_READ_ONLY_TOOL)
async def consultar_parcela_por_codigo(
    ctx: Context[AppContext],
    codigo_parcela: Annotated[
        str,
        Field(
            min_length=1,
            max_length=64,
            description="Código de parcela catastral de 14 caracteres.",
        ),
    ],
    incluir_raw: Annotated[
        bool, Field(description="Incluir respuesta original para diagnóstico")
    ] = False,
) -> CatastroResponse:
    """Consulta todos los inmuebles asociados a una parcela catastral."""
    resultado = (
        await ctx.request_context.lifespan_context.catastro_service.consultar_parcela_por_codigo(
            codigo_parcela, incluir_raw
        )
    )
    return resultado


@app.resource(
    "catastro://api/info",
    name="informacion_api_catastro",
    title="Información de la API del Catastro",
    description="Endpoints, capacidades y ejemplos del servidor.",
    mime_type="application/json",
)
def informacion_api_catastro() -> dict[str, Any]:
    """Describe las capacidades del servidor Catastro MCP."""
    return {
        "version": settings.app_version,
        "sdk_mcp": "2.x",
        "revision": settings.revision,
        "contrato": "2.0",
        "limites": {
            "tiempo_total_segundos": settings.catastro_total_timeout,
            "concurrencia": settings.catastro_max_concurrency,
            "cache_ttl_segundos": settings.catastro_cache_ttl,
            "cache_callejero_ttl_segundos": settings.catastro_catalogue_cache_ttl,
        },
        "description": "Servidor MCP para consultas al Catastro de España",
        "herramientas_disponibles": [
            "consultar_catastro_por_referencia",
            "consultar_catastro_por_coordenadas",
            "buscar_catastro_por_direccion",
            "generar_resumen_ia",
            "validar_referencia_catastral",
            "consultar_parcela_por_codigo",
        ],
        "importante": "Dirección y coordenadas devuelven candidatos; la consulta local no acredita titularidad ni valor catastral.",
        "cobertura": "Dirección General del Catastro, incluidas Canarias; Navarra y País Vasco tienen catastros propios.",
        "ejemplos_funcionales": {
            "referencia_completa": "4611123VG4141B0013RS",
            "referencia_parcial": "2314501EG1421S",
            "coordenadas": {"latitud": 41.9252415752936, "longitud": 3.14946484974333},
        },
    }


def main() -> None:
    """Ejecuta el servidor mediante el transporte stdio."""
    configure_logging(settings)
    logger.info("Iniciando Catastro MCP con el SDK v2")
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
