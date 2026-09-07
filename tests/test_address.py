from copy import deepcopy

import httpx
import pytest

from mcp_server import parse_direccion_completa
from services.catastro_service import CatastroService
from tests.test_catastro_responses import fixture


def address_response(request):
    path = request.url.path
    if path.endswith("ObtenerMunicipios"):
        return httpx.Response(200, json=fixture("municipalities"))
    if path.endswith("ObtenerCallejero"):
        assert request.url.params["NomVia"] == "REYES CATOLICOS"
        return httpx.Response(200, json=fixture("streets"))
    assert path.endswith("Consulta_DNPLOC")
    assert request.url.params["Sigla"] == "CL"
    assert request.url.params["Calle"] == "REYES CATOLICOS"
    assert request.url.params["Numero"] == "6"
    return httpx.Response(200, json=fixture("address"))


@pytest.mark.asyncio
async def test_real_address_list_and_interior_parameters():
    calls = []

    def handler(request):
        calls.append(request)
        return address_response(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await CatastroService(client).buscar_por_direccion(
            "GRANADA",
            "ARMILLA",
            "CALLE",
            "REYES CATOLICOS",
            "6",
            escalera="1",
            planta="00",
            puerta="A",
        )
    assert result.estado_consulta == "exitosa"
    assert result.total_inmuebles == 22 and result.requiere_seleccion
    assert calls[-1].url.params["Escalera"] == "1"
    assert calls[-1].url.params["Puerta"] == "A"
    assert result.inmuebles[12].referencia_catastral == "4611123VG4141B0013RS"


@pytest.mark.asyncio
async def test_ambiguous_streets_are_not_arbitrarily_selected():
    def handler(request):
        if request.url.path.endswith("ObtenerMunicipios"):
            return httpx.Response(200, json=fixture("municipalities"))
        assert request.url.path.endswith("ObtenerCallejero")
        raw = deepcopy(fixture("streets"))
        street = deepcopy(raw["consulta_callejeroResult"]["callejero"]["calle"][0])
        street["dir"]["tv"] = "AV"
        street["dir"]["cv"] = "183"
        raw["consulta_callejeroResult"]["callejero"]["calle"].append(street)
        return httpx.Response(200, json=raw)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await CatastroService(client).buscar_por_direccion(
            "GRANADA", "ARMILLA", nombre_via="REYES CATOLICOS", numero="6"
        )
    assert result.estado_consulta == "requiere_seleccion"
    assert len(result.candidatos) == 2
    assert {c.tipo_via for c in result.candidatos} == {"CL", "AV"}
    assert not result.inmuebles


@pytest.mark.asyncio
async def test_missing_number_returns_street_without_unbounded_property_search():
    async with httpx.AsyncClient(transport=httpx.MockTransport(address_response)) as client:
        result = await CatastroService(client).buscar_por_direccion(
            "GRANADA", "ARMILLA", nombre_via="REYES CATOLICOS"
        )
    assert result.estado_consulta == "requiere_seleccion"
    assert "número" in result.advertencias[0]


@pytest.mark.parametrize(
    "text,name,number",
    [
        ("CALLE MAYOR, MADRID, MADRID", "MAYOR", ""),
        ("CALLE MAYOR 3 BIS, MADRID, MADRID", "MAYOR", "3 BIS"),
        ("AVENIDA DEL 2 DE MAYO 6, 28000, MADRID, MADRID", "DEL 2 DE MAYO", "6"),
        ("CL MAYOR S/N, MADRID, MADRID", "MAYOR", "S/N"),
    ],
)
def test_text_adapter_does_not_treat_street_name_as_number(text, name, number):
    result = parse_direccion_completa(text)
    assert result["nombre_via"] == name and result["numero"] == number
