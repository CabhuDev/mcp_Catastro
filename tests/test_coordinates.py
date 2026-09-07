import httpx
import pytest

from services.catastro_service import CatastroService
from tests.test_catastro_responses import fixture


@pytest.mark.asyncio
@pytest.mark.parametrize("lat,lon", [(41.9252415752936, 3.14946484974333), (28.128, -15.434)])
async def test_coordinates_resolve_parcel_and_preserve_candidates(lat, lon):
    calls = []

    def handler(request):
        calls.append(request)
        if request.url.path.endswith("Consulta_RCCOOR"):
            assert dict(request.url.params) == {
                "SRS": "EPSG:4326",
                "CoorX": str(lon),
                "CoorY": str(lat),
            }
            return httpx.Response(200, json=fixture("coordinates"))
        assert request.url.params["RefCat"] == "2314501EG1421S"
        return httpx.Response(200, json=fixture("parcel_multiple"))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await CatastroService(client).consultar_por_coordenadas(lat, lon, incluir_raw=True)
    assert len(calls) == 2
    assert result.estado_consulta == "exitosa"
    assert result.total_inmuebles == 7 and result.requiere_seleccion
    assert result.coordenadas.latitud == lat
    assert result.datos_raw["coordenadas"] == fixture("coordinates")


@pytest.mark.asyncio
@pytest.mark.parametrize("code,status", [("76", "error_formato"), ("16", "sin_datos")])
async def test_coordinate_error_is_preserved(code, status):
    def handler(request):
        assert request.url.path.endswith("Consulta_RCCOOR")
        return httpx.Response(
            200,
            json={
                "Consulta_RCCOORResult": {
                    "control": {"cuerr": 1},
                    "lerr": [{"cod": code, "des": "Mensaje oficial"}],
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await CatastroService(client).consultar_por_coordenadas(40.4168, -3.7038)
    assert result.estado_consulta == status and result.codigo_error == code


@pytest.mark.asyncio
async def test_invalid_coordinates_do_not_raise_again_in_error_handler():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: pytest.fail("Unexpected request"))
    ) as client:
        service = CatastroService(client)
        invalid = await service.consultar_por_coordenadas(1000, 0)
        outside = await service.consultar_por_coordenadas(0, 0)
    assert invalid.codigo_error == "ENTRADA_INVALIDA"
    assert outside.codigo_error == "FUERA_COBERTURA"
