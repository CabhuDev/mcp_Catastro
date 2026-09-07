"""Regresiones con respuestas públicas capturadas el 7 de septiembre de 2026."""

import json
from pathlib import Path

import httpx
import pytest

from services.catastro_service import CatastroService

FIXTURES = Path(__file__).parent / "fixtures" / "catastro"


def fixture(name):
    return json.loads((FIXTURES / (name + ".json")).read_text())


@pytest.mark.asyncio
async def test_reference_preserves_address_and_constructions():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=fixture("reference")))
    ) as client:
        result = await CatastroService(client).consultar_por_referencia("4611123VG4141B0013RS")
    assert result.estado_consulta == "exitosa"
    assert result.direccion.numero == "6"
    assert result.direccion.codigo_postal == "18100"
    assert result.direccion.escalera == "1"
    assert result.superficie_parcela == 304
    assert result.datos_basicos.superficie_suelo is None
    assert result.inmuebles[0].construcciones[0].superficie == 46
    assert result.datos_raw is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "name,ref,count",
    [
        ("parcel_single", "4418928VG4141G", 1),
        ("parcel_multiple", "2314501EG1421S", 7),
        ("rural", "13077A01800039", 1),
    ],
)
async def test_parcel_variants(name, ref, count):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=fixture(name)))
    ) as client:
        result = await CatastroService(client).consultar_parcela_por_codigo(ref)
    assert result.estado_consulta == "exitosa"
    assert result.total_inmuebles == count
    assert result.mensaje_error is None
    assert result.requiere_seleccion == (count > 1)
    if count == 7:
        assert result.inmuebles[0].direccion.provincia_codigo_ine == "17"
        assert result.inmuebles[0].datos_basicos.superficie_construida == 6863
        assert result.datos_basicos is None
    if name == "rural":
        assert result.direccion.poligono == "18"
        assert result.direccion.parcela_rustica == "39"


@pytest.mark.asyncio
async def test_xml_matches_json():
    async with httpx.AsyncClient() as client:
        service = CatastroService(client)
        xml = service._parsear_respuesta_json((FIXTURES / "reference.xml").read_text())
        left = service._construir_respuesta_catastral("4611123VG4141B0013RS", xml)
        right = service._construir_respuesta_catastral("4611123VG4141B0013RS", fixture("reference"))
        assert left.estado_consulta == right.estado_consulta == "exitosa"
        assert left.direccion == right.direccion
        assert left.inmuebles[0].construcciones == right.inmuebles[0].construcciones
        assert left.datos_basicos.superficie_construida == right.datos_basicos.superficie_construida
        with pytest.raises(ValueError):
            service._parsear_respuesta_json("<html><body>Maintenance</body></html>")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,status",
    [
        ("4", "error_formato"),
        ("76", "error_formato"),
        ("5", "sin_datos"),
        ("16", "sin_datos"),
        ("99", "error"),
    ],
)
async def test_provider_errors_are_not_hidden(code, status):
    raw = {
        "consulta_dnprcResult": {
            "control": {"cuerr": 1},
            "lerr": [{"cod": code, "des": "Mensaje oficial"}],
        }
    }
    async with httpx.AsyncClient() as client:
        result = CatastroService(client)._construir_respuesta_catastral(
            "ref", raw, incluir_raw=True
        )
    assert result.estado_consulta == status
    assert result.codigo_error == code
    assert result.mensaje_error == "Mensaje oficial"
    assert result.datos_raw == raw
