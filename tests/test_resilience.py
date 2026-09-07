import asyncio

import httpx
import pytest

from services.catastro_service import CatastroService
from tests.test_catastro_responses import fixture

REF = "4611123VG4141B0013RS"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,expected",
    [(400, 1), (401, 1), (404, 1), (429, 3), (500, 3), (502, 3), (503, 3), (504, 3)],
)
async def test_retry_only_transient_status(status, expected):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, headers={"Retry-After": "0"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = CatastroService(client)
        service.max_retries = 2
        service.retry_delay = 0
        result = await service.consultar_por_referencia(REF)
    assert len(calls) == expected
    assert result.codigo_error == f"HTTP_{status}"


@pytest.mark.asyncio
async def test_total_budget_covers_retry_after():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "60"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = CatastroService(client)
        service.settings.catastro_total_timeout = 0.02
        result = await service.consultar_por_referencia(REF)
    assert result.codigo_error == "TIMEOUT"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_cache_is_bounded_expires_and_returns_copies():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=fixture("reference"))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = CatastroService(client)
        service.settings.catastro_cache_size = 1
        first = await service.consultar_por_referencia(REF, incluir_raw=True)
        first.datos_raw.clear()
        second = await service.consultar_por_referencia(REF, incluir_raw=True)
        assert second.total_inmuebles == 1 and second.datos_raw
        assert len(calls) == 1
        key = next(iter(service._cache))
        service._cache[key] = (0, service._cache[key][1])
        await service.consultar_por_referencia(REF)
        assert len(calls) == 2
        await service.consultar_parcela_por_codigo(REF[:14])
        assert len(service._cache) == 1
        await service.consultar_por_referencia(REF)
        assert len(calls) == 4


@pytest.mark.asyncio
async def test_errors_are_not_cached_or_retried_as_empty_results():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "consulta_dnprcResult": {
                    "control": {"cuerr": 1},
                    "lerr": [{"cod": "4", "des": "Inválida"}],
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = CatastroService(client)
        await service.consultar_por_referencia(REF)
        await service.consultar_por_referencia(REF)
        assert not service._cache
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_requests_obey_concurrency_limit(monkeypatch):
    monkeypatch.setenv("CATASTRO_MAX_CONCURRENCY", "2")
    active = peak = 0

    async def handler(request):
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, json=fixture("reference"))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = CatastroService(client)
        results = await asyncio.gather(*(service.consultar_por_referencia(REF) for _ in range(6)))
    assert peak == 2
    assert all(r.estado_consulta == "exitosa" for r in results)


@pytest.mark.asyncio
async def test_external_cancellation_is_not_swallowed():
    started = asyncio.Event()

    async def handler(request):
        started.set()
        await asyncio.Event().wait()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        task = asyncio.create_task(CatastroService(client).consultar_por_referencia(REF))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


@pytest.mark.asyncio
async def test_malformed_success_is_not_cached():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"consulta_dnprcResult": {"control": {"cudnp": 1}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        service = CatastroService(client)
        result = await service.consultar_por_referencia(REF)
        await service.consultar_por_referencia(REF)
        assert not service._cache
    assert len(calls) == 2
    assert result.codigo_error == "RESPUESTA_INVALIDA"
