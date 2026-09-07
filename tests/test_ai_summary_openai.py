"""Compatibilidad de la integración opcional con OpenAI 3.x."""

import builtins
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.catastro_models import CatastroResponse
from services.ai_summary import AIService


def _datos() -> CatastroResponse:
    return CatastroResponse(referencia_catastral="2314501EG1421S0001KJ")


def _service(monkeypatch: pytest.MonkeyPatch, *, api_key: str | None = "test-key") -> AIService:
    if api_key is None:
        monkeypatch.delenv("CATASTRO_OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("CATASTRO_OPENAI_API_KEY", api_key)
    catastro_service = SimpleNamespace(consultar_por_referencia=AsyncMock(return_value=_datos()))
    return AIService(catastro_service=catastro_service)


@pytest.mark.asyncio
async def test_openai_client_parameters_and_response(monkeypatch: pytest.MonkeyPatch) -> None:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  Resumen remoto  "))]
    )
    create = AsyncMock(return_value=completion)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    async_openai = MagicMock(return_value=client)
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=async_openai))
    monkeypatch.setenv("CATASTRO_OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("CATASTRO_OPENAI_MAX_TOKENS", "321")
    monkeypatch.setenv("CATASTRO_OPENAI_TEMPERATURE", "0.2")
    service = _service(monkeypatch)

    result = await service.generar_resumen(_datos().referencia_catastral, usar_openai=True)

    assert result.resumen == "Resumen remoto"
    assert result.metodo_usado == "openai"
    assert result.motivo_degradacion is None
    async_openai.assert_called_once_with(api_key="test-key")
    create.assert_awaited_once()
    request = create.await_args.kwargs
    assert request["model"] == "gpt-test"
    assert request["max_tokens"] == 321
    assert request["temperature"] == 0.2
    assert request["messages"][0]["role"] == "system"
    assert request["messages"][1]["role"] == "user"
    assert _datos().referencia_catastral in request["messages"][1]["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("content", [None, "", "   "])
async def test_empty_openai_content_uses_local_fallback(
    monkeypatch: pytest.MonkeyPatch, content: str | None
) -> None:
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=completion)))
    )
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(AsyncOpenAI=MagicMock(return_value=client)),
    )
    service = _service(monkeypatch)

    result = await service.generar_resumen(_datos().referencia_catastral, usar_openai=True)

    assert "Resumen Catastral" in result.resumen
    assert result.metodo_usado == "plantilla"
    assert result.motivo_degradacion is not None


@pytest.mark.asyncio
async def test_openai_api_error_uses_local_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("API failure")))
        )
    )
    monkeypatch.setitem(
        sys.modules,
        "openai",
        SimpleNamespace(AsyncOpenAI=MagicMock(return_value=client)),
    )
    service = _service(monkeypatch)

    result = await service.generar_resumen(_datos().referencia_catastral, usar_openai=True)

    assert "Resumen Catastral" in result.resumen
    assert result.metodo_usado == "plantilla"
    assert result.motivo_degradacion is not None


@pytest.mark.asyncio
async def test_missing_api_key_does_not_import_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service(monkeypatch, api_key=None)
    real_import = builtins.__import__

    def guarded_import(name: str, *args: object, **kwargs: object) -> object:
        if name == "openai":
            raise AssertionError("OpenAI should not be imported without an API key")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    result = await service.generar_resumen(_datos().referencia_catastral, usar_openai=True)

    assert "Resumen Catastral" in result.resumen
    assert result.metodo_usado == "plantilla"
    assert result.motivo_degradacion is not None


@pytest.mark.asyncio
async def test_missing_optional_dependency_uses_local_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(monkeypatch)
    real_import = builtins.__import__

    def missing_openai(name: str, *args: object, **kwargs: object) -> object:
        if name == "openai":
            raise ModuleNotFoundError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_openai)

    result = await service.generar_resumen(_datos().referencia_catastral, usar_openai=True)

    assert "Resumen Catastral" in result.resumen
    assert result.metodo_usado == "plantilla"
    assert result.motivo_degradacion is not None


@pytest.mark.asyncio
async def test_summary_includes_full_address_without_historical_claims(monkeypatch):
    from models.catastro_models import DatosBasicosInmueble, DireccionCatastral

    service = _service(monkeypatch, api_key=None)
    data = _datos()
    data.datos_basicos = DatosBasicosInmueble(antiguedad=1900, superficie_construida=52)
    data.direccion = DireccionCatastral(
        via="CL MAYOR",
        numero="6",
        escalera="1",
        planta="00",
        puerta="A",
        codigo_postal="18100",
        municipio="ARMILLA",
    )
    service.catastro_service.consultar_por_referencia.return_value = data
    result = await service.generar_resumen(data.referencia_catastral)
    assert "18100" in result.resumen and "Esc. 1" in result.resumen
    assert "histórico" not in result.resumen
    assert result.motivo_degradacion is None


@pytest.mark.asyncio
async def test_openai_client_is_closed(monkeypatch):
    service = _service(monkeypatch)
    service._openai_client = SimpleNamespace(close=AsyncMock())
    await service.aclose()
    service._openai_client.close.assert_awaited_once()
