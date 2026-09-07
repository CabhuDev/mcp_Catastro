# Respuestas de regresión

Capturadas mediante consultas públicas de lectura a `ovc.catastro.meh.es` el 7 de septiembre de 2026. No contienen titulares ni valores protegidos. Son ejemplos del contrato del proveedor, no una copia actualizada del Catastro.

- `reference.json` / `.xml`: `4611123VG4141B0013RS`, WCF JSON y ASMX XML. El XML no incluye toda la información de finca del JSON; ambos contienen dirección y construcciones.
- `parcel_single.json`: `4418928VG4141G`, variante `bico`.
- `parcel_multiple.json`: `2314501EG1421S`, siete elementos `lrcdnp.rcdnp`; superficie con punto de miles.
- `rural.json`: `13077A01800039`, referencia completa devuelta `13077A018000390000MS`.
- `coordinates.json`: `CoorX=3.14946484974333`, `CoorY=41.9252415752936`, `SRS=EPSG:4326`.
- `address.json`: `GRANADA/ARMILLA/CL/REYES CATOLICOS/6`, sin filtro interior, 22 inmuebles.
- `municipalities.json`, `streets.json`: resolución oficial de ARMILLA y REYES CATOLICOS.

El control de las referencias se contrasta con las referencias devueltas por el proveedor. El ejemplo didáctico rústico que termina en FP en algunas páginas no coincide con la referencia MS que devuelve actualmente esta consulta.
