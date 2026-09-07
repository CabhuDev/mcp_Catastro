import pytest
from pydantic import ValidationError

from models.catastro_models import ReferenciaCatastral


@pytest.mark.parametrize(
    "ref",
    [
        "2314501EG1421S0001KJ",
        "4611123VG4141B0013RS",
        "4418928VG4141G0001IW",
        "13077A018000390000MS",
        "4A08169P03PRAT0001LR",
    ],
)
def test_known_references_and_control_mutations(ref):
    assert ReferenciaCatastral(referencia=ref).referencia == ref
    invalid = ref[:-1] + ("A" if ref[-1] != "A" else "B")
    with pytest.raises(ValidationError):
        ReferenciaCatastral(referencia=invalid)


def test_normalization_and_validation_meaning():
    assert (
        ReferenciaCatastral(referencia="2314501 eg1421s-0001 kj").referencia
        == "2314501EG1421S0001KJ"
    )
    analysis = ReferenciaCatastral.analizar_referencia_detallado("2314501EG1421S")
    assert analysis["es_valida"] and analysis["es_codigo_parcela"]
    assert analysis["control_valido"] is None
    assert analysis["existencia_confirmada"] is None
    assert not ReferenciaCatastral.analizar_referencia_detallado("A" * 20)["es_valida"]
    assert not ReferenciaCatastral.analizar_referencia_detallado("!" * 14)["es_valida"]
