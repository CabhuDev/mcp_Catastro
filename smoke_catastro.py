"""Smoke test de las seis herramientas MCP locales contra Catastro real.

Ejecutar manualmente: uv run --locked python smoke_catastro.py
No forma parte de pytest/CI para no depender de disponibilidad externa.
"""

import asyncio
import json

from mcp import Client

from config.settings import configure_logging
from mcp_server import app


async def main() -> None:
    cases = [
        ("validar_referencia_catastral", {"referencia": "4611123VG4141B0013RS"}),
        ("consultar_catastro_por_referencia", {"referencia": "4611123VG4141B0013RS"}),
        ("consultar_parcela_por_codigo", {"codigo_parcela": "4418928VG4141G"}),
        (
            "consultar_catastro_por_coordenadas",
            {"latitud": 41.9252415752936, "longitud": 3.14946484974333},
        ),
        (
            "buscar_catastro_por_direccion",
            {
                "provincia": "GRANADA",
                "municipio": "ARMILLA",
                "tipo_via": "CL",
                "nombre_via": "REYES CATOLICOS",
                "numero": "6",
                "escalera": "1",
                "planta": "00",
                "puerta": "A",
            },
        ),
        ("generar_resumen_ia", {"referencia": "4611123VG4141B0013RS", "usar_openai": False}),
    ]
    async with Client(app) as client:
        info = await client.read_resource("catastro://api/info")
        print(info.contents[0].text)
        for name, args in cases:
            result = await client.call_tool(name, args)
            data = result.structured_content
            if result.is_error or not data:
                raise RuntimeError(f"{name}: error MCP")
            if name == "validar_referencia_catastral":
                success = data["es_valida"]
            elif name == "generar_resumen_ia":
                success = data["estado"] == "exitosa" and data["metodo_usado"] == "plantilla"
            else:
                success = data["estado_consulta"] == "exitosa" and data["total_inmuebles"] > 0
            print(
                json.dumps(
                    {
                        "tool": name,
                        "ok": success,
                        "inmuebles": data.get("total_inmuebles"),
                        "codigo_error": data.get("codigo_error"),
                    },
                    ensure_ascii=False,
                )
            )
            if not success:
                raise RuntimeError(f'{name}: {data.get("mensaje_error", "fallo funcional")}')


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
