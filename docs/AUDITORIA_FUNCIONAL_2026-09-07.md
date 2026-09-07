# Auditoría funcional del MCP Catastro

**Documento histórico del diagnóstico previo a las correcciones.** El estado implementado y la migración están en el [README](../README.md).

Fecha: 7 de septiembre de 2026. Código local revisado: `e8239ea`.

Se probaron las seis herramientas del conector desplegado, con el resumen en modo local. Se contrastaron sus resultados con peticiones HTTP de lectura a Catastro y con el código local. No se ha comprobado el SHA del servidor remoto ni modificado el despliegue. Los fallos descritos del conector coinciden con la implementación local. El modo OpenAI no se ha probado en producción.

## Resultado por herramienta

| Herramienta | Resultado observado |
|---|---|
| `buscar_catastro_por_direccion` | No implementa búsqueda; devuelve siempre información y alternativas para entradas completas. |
| `consultar_catastro_por_coordenadas` | Rota: parámetros incorrectos, lectura incorrecta de la respuesta y posterior incompatibilidad entre referencia de parcela e inmueble. |
| `consultar_parcela_por_codigo` | Devuelve los 7 inmuebles de `2314501EG1421S`, pero omite una parcela existente con un solo inmueble y genera componentes geográficos incorrectos. |
| `consultar_catastro_por_referencia` | Funciona en los dos casos positivos probados; pierde número, código postal y escalera en los datos estructurados. Oculta errores de Catastro como ausencia de datos. |
| `validar_referencia_catastral` | Solo verifica longitud y alfanuméricos; acepta `AAAAAAAAAAAAAAAAAAAA` como válida. No verifica estructura ni control ni existencia. |
| `generar_resumen_ia` | Funciona como plantilla local; hereda los datos omitidos. El modo OpenAI puede degradarse a plantilla sin informar al consumidor. |

## 1. Coordenadas: tres fallos encadenados

Ubicación del código: `services/catastro_service.py:100`, `:641`; restricciones en `mcp_server.py:179` y `models/catastro_models.py:154` aproximadamente.

1. Envía `Coordenada_X` / `Coordenada_Y`. La operación WCF utilizada exige `CoorX` / `CoorY`. El conector devuelve `sin_datos`, pero la respuesta original contiene el error 76, `LA COORDENADA X OBLIGATORIA`.
2. El extractor busca `consulta_rccoorResult` y campos `refcat`/`pc` de primer nivel. La respuesta real utiliza `Consulta_RCCOORResult.coordenadas.coord[]`, con `pc.pc1` y `pc.pc2`.
3. Concatenar `pc1+pc2` produce 14 caracteres. El siguiente paso llama a `consultar_por_referencia`, cuyo modelo exige 20. Debe consultar la parcela y devolver sus inmuebles como candidatos; un punto no identifica una planta o puerta.

Prueba positiva independiente: `Consulta_CPMRC` para `2314501EG1421S` devolvió longitud `3.14946484974333`, latitud `41.9252415752936`. La llamada correcta a `Consulta_RCCOOR` en ese punto devolvió la misma parcela. El extractor local devolvió `DESCONOCIDA` al procesar esa respuesta positiva. El conector desplegado siguió devolviendo el error 76 encubierto.

Petición reproducible:

```sh
curl --get 'https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/Consulta_RCCOOR' \
  --data-urlencode 'SRS=EPSG:4326' \
  --data-urlencode 'CoorX=3.14946484974333' \
  --data-urlencode 'CoorY=41.9252415752936'
```

Además, los límites 35–44 de latitud y −10–5 de longitud excluyen Canarias antes de consultar. Hay que separar validación geográfica de cobertura del proveedor. Los puntos de ejemplo en espacio público pueden no tener referencia: con parámetros correctos, `40.4168,-3.7038` devolvió error 16, que sí corresponde a ausencia de referencia.

## 2. Dirección: la API sí funciona

Ubicación: `services/catastro_service.py:691`, `mcp_server.py:72` y `:244`.

`buscar_por_direccion` no realiza ninguna petición HTTP. Su afirmación de que los endpoints JSON no están operativos queda contradicha por la prueba realizada:

```sh
curl --get 'https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/json/Consulta_DNPLOC' \
  --data-urlencode 'Provincia=GRANADA' --data-urlencode 'Municipio=ARMILLA' \
  --data-urlencode 'Sigla=CL' --data-urlencode 'Calle=REYES CATOLICOS' \
  --data-urlencode 'Numero=6' --data-urlencode 'Bloque=' \
  --data-urlencode 'Escalera=' --data-urlencode 'Planta=' --data-urlencode 'Puerta='
```

Resultado: `consulta_dnplocResult.control.cudnp=22`, con 22 inmuebles. Uno es `4611123VG4141B0013RS`, residencial de 52 m², escalera 1, planta 00, puerta A.

Implementar `Consulta_DNPLOC` con entradas estructuradas: provincia, municipio, tipo/nombre de vía y número; bloque, escalera, planta y puerta opcionales. Usar el callejero oficial para resolver nombres/códigos y presentar alternativas cuando exista ambigüedad. Conservar texto libre como interfaz auxiliar, sin depender exclusivamente de separar comas. El parser actual interpreta `CALLE MAYOR, MADRID, MADRID` como nombre vacío y número `MAYOR`.

Actualizar descripción, instrucciones del servidor, recurso informativo, README y anotación `open_world_hint` al habilitar la llamada externa. No se necesita Google Maps ni una clave de geocodificación para el caso demostrado.

## 3. Parcelas: falso negativo y geografía inventada

Ubicación: `services/catastro_service.py:903` y `:1090`.

- `2314501EG1421S`: el conector devuelve correctamente 7 inmuebles, pero identifica provincia `23` y municipio `145` cortando la referencia. Los datos oficiales dicen GIRONA (`17`), PALAFRUGELL (`117` INE; `124` catastral).
- `4418928VG4141G`: la API devuelve `bico`, `cudnp=1`, inmueble `4418928VG4141G0001IW`. El extractor solo contempla `lrcdnp.rcdnp`; el conector declara que no existe o no tiene inmuebles.

Aceptar ambas variantes y normalizarlas a una lista, sin llamar «división horizontal» a cualquier resultado. No deducir provincia/municipio de una referencia urbana. Diferenciar códigos INE y catastrales, usando los campos del proveedor. La estructura urbana y rústica son distintas.

## 4. Referencias, datos y errores

Ubicación: `models/catastro_models.py:28`, `:43`; `services/catastro_service.py:328`, `:370`.

- El validador desplegado responde `es_valida=true` para veinte letras A. Al consultar esa cadena, Catastro devuelve error 4: referencia incorrectamente formada. El servicio local lo traduce a `sin_datos`.
- Separar `formato_valido`, `control_valido` y `existencia_confirmada`; validar formatos urbano/rústico y caracteres de control con casos contrastados. Una validación local no demuestra existencia. Reconocer 14 caracteres como código de parcela utilizable.
- Para `4611123VG4141B0013RS`, el conector devuelve `numero=null` y `codigo_postal=null` pese a que la respuesta original contiene `dir.pnp=6`, `lourb.dp=18100` y `loint.es=1`. Falta extraerlos y añadir escalera al modelo. También se omiten detalles de construcciones y superficie de parcela disponibles en el caso probado.
- Normalizar unidades/números según campo y formato: en el listado de parcela la superficie aparece como `6.863`, mientras el detalle individual devuelve `6863`. No aplicar una conversión genérica que pueda transformar miles en decimales.
- Interpretar `control.cuerr` y `lerr` antes de extraer datos. Distinguir entrada inválida, ausencia real, error remoto, timeout y fallo de parsing. Mantener el código y mensaje de origen. Una respuesta HTTP 200 no garantiza éxito funcional.

## 5. XML, resumen y contrato de respuesta

- El fallback XML no equivale a un adaptador funcional: una respuesta XML real de `OVCCallejero.asmx/Consulta_DNPRC` contiene `bico` con namespace; el parser conserva etiquetas `{http://www.catastro.meh.es/}bico` y el consumidor espera `consulta_dnprcResult`. Resultado reproducido: `sin_datos` pese a contener el inmueble. Normalizar namespaces y envolturas si se mantiene ese soporte; rechazar HTML como respuesta inesperada.
- El resultado de parcela mezcla texto de éxito en `mensaje_error`, lista procesada dentro de `datos_raw` y copia adicional de la respuesta original. Definir modelos explícitos de inmueble, parcela, candidatos y error, con datos originales opcionales para diagnóstico.
- El resumen local probado funciona. Si `usar_openai=true` y falta clave, o falla OpenAI, devuelve la plantilla sin informar del método real. Devolver `metodo_usado` y causa de degradación. La instalación opcional y la clave/modelo deben verificarse antes de afirmar que OpenAI funciona.
- Para uso mediante un asistente, valorar que el MCP entregue datos fiables y que el asistente redacte: evita otra consulta al Catastro, otra llamada a un modelo y configuración duplicada. Si se mantiene el resumen, evitar inferencias no sustentadas: tener más de 50 años no acredita carácter histórico ni estado de conservación.

## Plan recomendado y verificación de cierre

1. Corregir errores de proveedor, normalizar las respuestas de inmueble/lista y recuperar dirección completa.
2. Reparar el recorrido completo coordenadas → parcela → candidatos; admitir Canarias en la validación y explicar cobertura.
3. Implementar dirección estructurada y resolución de ambigüedades mediante el callejero.
4. Corregir validación de referencias, componentes territoriales y contrato de salida; aclarar modo de resumen y documentación.
5. Añadir pruebas de regresión basadas en respuestas reales guardadas: coordenadas positivas y errores 76/16, dirección con 22 candidatos, parcela `bico` y `lrcdnp`, referencia inválida, número/CP/escalera y XML válido. Hacer smoke tests contra el conector después del despliegue, incluyendo el SHA desplegado en la información operativa.

`uv run --locked pytest -q`: **15 passed**. Son pruebas de protocolo, ciclo de vida, seguridad/logging y OpenAI simulado; no aseguran estos recorridos reales. La prueba de dirección incluso espera `estado_consulta=informacion`. Los archivos `test-*.py` no se recogen con el patrón configurado `test_*.py`.

Como mejora posterior, añadir presupuesto total de tiempo, reintentos selectivos para errores transitorios, límites de concurrencia y caché breve para callejero/consultas repetidas. El README se contradice respecto a rate limiting: declara que no existe y después anuncia 60 consultas/minuto. No se debe presentar como implementado.

## Fuentes oficiales

- [Contrato WCF de Consulta_RCCOOR](https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/help/operations/Consulta_RCCOOR).
- [Servicios web libres del Catastro](https://www.catastro.hacienda.gob.es/ws/Webservices_Libres.pdf).
- [Estructuras de referencia urbana y rústica](https://www.catastro.hacienda.gob.es/es-ES/referencia_catastral.html).

Las comprobaciones positivas demuestran disponibilidad en los casos y momento probados; no garantizan cobertura universal ni disponibilidad permanente de Catastro.
