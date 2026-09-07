"""Garantías de privacidad y compatibilidad de logging con stdio."""

import asyncio
import io
import json
import logging
import subprocess
import sys
from pathlib import Path

import httpx
import pytest

from config.settings import Settings, configure_logging, log_failure, log_sensitive
from services.catastro_service import CatastroService

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _settings(monkeypatch: pytest.MonkeyPatch, *, level: str, sensitive: bool) -> Settings:
    monkeypatch.setenv("CATASTRO_LOG_LEVEL", level)
    monkeypatch.setenv("CATASTRO_LOG_SENSITIVE_DATA", str(sensitive).lower())
    return Settings()


def test_sensitive_values_are_hidden_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.StringIO()
    settings = _settings(monkeypatch, level="DEBUG", sensitive=False)
    configure_logging(settings, stream=stream)
    logger = logging.getLogger("catastro.test")

    sensitive_values = (
        "PRIVATE-REF-123",
        "40.123456,-3.654321",
        "CALLE PRIVADA 99",
        "PRIVATE_RAW_PAYLOAD",
    )
    logger.info("Consulta iniciada")
    for value in sensitive_values:
        log_sensitive(logger, settings.log_sensitive_data, "Dato: %s", value)
    log_failure(
        logger,
        logging.ERROR,
        settings.log_sensitive_data,
        "Consulta fallida",
        ValueError(sensitive_values[0]),
    )

    output = stream.getvalue()
    assert "Consulta iniciada" in output
    assert "Consulta fallida (ValueError)" in output
    assert all(value not in output for value in sensitive_values)
    assert logging.getLogger("mcp").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING


def test_sensitive_values_require_flag_and_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.StringIO()
    settings = _settings(monkeypatch, level="INFO", sensitive=True)
    configure_logging(settings, stream=stream)
    logger = logging.getLogger("catastro.test")
    log_sensitive(logger, settings.log_sensitive_data, "Referencia: %s", "PRIVATE-REF")
    assert "PRIVATE-REF" not in stream.getvalue()

    stream = io.StringIO()
    settings = _settings(monkeypatch, level="DEBUG", sensitive=True)
    configure_logging(settings, stream=stream)
    logger = logging.getLogger("catastro.test")
    log_sensitive(logger, settings.log_sensitive_data, "Referencia: %s", "PRIVATE-REF")
    assert "PRIVATE-REF" in stream.getvalue()


def test_service_logs_hide_inputs_and_raw_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    async def run() -> None:
        stream = io.StringIO()
        settings = _settings(monkeypatch, level="DEBUG", sensitive=False)
        configure_logging(settings, stream=stream)
        service = CatastroService(
            httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda r: httpx.Response(
                        200,
                        json={
                            "consulta_municipieroResult": {
                                "control": {"cuerr": 1},
                                "lerr": [{"cod": "1", "des": "No disponible"}],
                            }
                        },
                    )
                )
            )
        )

        try:
            await service.consultar_por_referencia("PRIVATE-REF-123")
            await service.buscar_por_direccion(
                provincia="PROVINCIA PRIVADA",
                municipio="MUNICIPIO PRIVADO",
                nombre_via="CALLE PRIVADA",
                numero="99",
                direccion_original="CALLE PRIVADA 99, MUNICIPIO PRIVADO, PROVINCIA PRIVADA",
            )
            with pytest.raises(ValueError, match="Error parseando respuesta"):
                service._parsear_respuesta_json("PRIVATE_RAW_PAYLOAD")
        finally:
            await service.http_client.aclose()

        output = stream.getvalue()
        assert "Búsqueda por dirección solicitada" in output
        assert "Error consultando Catastro (ValidationError)" in output
        assert "PRIVATE" not in output

    asyncio.run(run())


def test_stdio_keeps_logs_out_of_stdout() -> None:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2026-07-28",
            "capabilities": {},
            "clientInfo": {"name": "privacy-test", "version": "1.0"},
        },
    }
    process = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "mcp_server.py")],
        input=json.dumps(request) + "\n",
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
        timeout=10,
        check=False,
    )

    stdout_lines = [line for line in process.stdout.splitlines() if line]
    assert len(stdout_lines) == 1
    assert json.loads(stdout_lines[0])["jsonrpc"] == "2.0"
    assert "Iniciando Catastro MCP" not in process.stdout
    assert "Iniciando Catastro MCP" in process.stderr
