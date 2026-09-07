"""Pruebas de seguridad XML y ciclo de vida del cliente HTTP."""

import asyncio

import httpx
import pytest

from mcp_server import app, app_lifespan
from services.catastro_service import CatastroService


def test_lifespan_reuses_and_closes_http_client() -> None:
    async def run() -> None:
        async with app_lifespan(app) as context:
            http_client = context.catastro_service.http_client

            assert context.ai_service.catastro_service is context.catastro_service
            assert context.ai_service.catastro_service.http_client is http_client
            assert http_client.is_closed is False

        assert http_client.is_closed is True

    asyncio.run(run())


def test_xml_parser_rejects_entities() -> None:
    async def run() -> None:
        malicious_xml = """<?xml version="1.0"?>
<!DOCTYPE data [<!ENTITY secret SYSTEM "file:///etc/passwd">]>
<data>&secret;</data>
"""
        service = CatastroService()

        try:
            with pytest.raises(ValueError, match="Error parseando respuesta"):
                service._parsear_respuesta_xml(malicious_xml)
        finally:
            await service.aclose()

    asyncio.run(run())


def test_catastro_query_with_mock_transport() -> None:
    async def run() -> None:
        reference = "2314501EG1421S0001KJ"

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["RefCat"] == reference
            return httpx.Response(
                200, json={"consulta_dnprcResult": {"control": {"cudnp": 0}}}, request=request
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            service = CatastroService(http_client=http_client)
            result = await service.consultar_por_referencia(reference)

        assert result.referencia_catastral == reference
        assert result.estado_consulta == "sin_datos"

    asyncio.run(run())
