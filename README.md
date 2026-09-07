# MCP Catastro España

Servidor MCP comunitario para consultar datos públicos de la Dirección General del Catastro. Este es el fork de [Báculum](https://github.com/baculummayores/mcp_catastro), basado en el trabajo de [CabhuDev](https://github.com/CabhuDev/mcp_Catastro). No es un servidor oficial del Gobierno.

Python 3.14, MCP Python SDK 2.x, transporte stdio. Versión de aplicación y contrato: **2.0.0**.

## Instalación

```sh
uv sync --locked
uv run --locked python mcp_server.py
```

OpenAI es opcional: `uv sync --locked --extra openai`. El servidor no necesita una clave para buscar por dirección, coordenadas, referencia o parcela. `uv.lock` es la resolución de dependencias utilizada por instalación y CI.

## Herramientas

| Herramienta | Entrada | Resultado |
|---|---|---|
| `consultar_catastro_por_referencia` | Referencia de 20 caracteres | Inmueble, dirección completa, construcciones y superficie de parcela cuando constan |
| `consultar_parcela_por_codigo` | Código de 14 caracteres | Lista de inmuebles, incluidos los casos sin división horizontal |
| `consultar_catastro_por_coordenadas` | Latitud/longitud WGS84 | Parcelas localizadas e inmuebles candidatos; no elige una planta o puerta |
| `buscar_catastro_por_direccion` | Campos de dirección o texto | Callejero y candidatos; permite filtrar escalera, planta y puerta |
| `validar_referencia_catastral` | Código de 14 o referencia de 20 caracteres | Formato, control y tipo; no confirma existencia |
| `generar_resumen_ia` | Referencia, idioma `es/en/ca`, `usar_openai` | Resumen, método real y motivo de degradación si lo hay |

Las cuatro herramientas de consulta admiten `incluir_raw=true` para diagnóstico. Por defecto no duplican las respuestas originales. El recurso `catastro://api/info` informa del contrato, límites y revisión desplegada (`CATASTRO_REVISION`).

### Búsqueda por dirección

```json
{
  "provincia": "GRANADA",
  "municipio": "ARMILLA",
  "tipo_via": "CL",
  "nombre_via": "REYES CATOLICOS",
  "numero": "6"
}
```

En la prueba del 7 de septiembre de 2026 devuelve 22 inmuebles. Para uno concreto, añadir `escalera: "1"`, `planta: "00"`, `puerta: "A"`; también admite `bloque`. Los nombres se resuelven contra el callejero oficial. Si hay varios municipios o vías compatibles, devuelve `candidatos` para elegir; si falta número, lo solicita sin consultar todos los inmuebles de la calle.

Se conserva `direccion_completa`, por ejemplo `CALLE REYES CATOLICOS 6, 18100, ARMILLA, GRANADA`. Los campos explícitos prevalecen sobre el texto. El código postal del texto no se usa como filtro: la consulta se resuelve con provincia, municipio, vía y número. Para nombres con comas u otros formatos ambiguos, usar campos estructurados.

### Coordenadas y cobertura

```json
{"latitud": 41.9252415752936, "longitud": 3.14946484974333}
```

Este punto devuelve la parcela `2314501EG1421S`, con siete inmuebles en la prueba. La coordenada de entrada no identifica planta ni puerta. Un punto en una plaza o calzada puede no tener referencia. Se admiten Canarias y coordenadas geográficas válidas; la disponibilidad depende de la DGC. País Vasco y Navarra tienen catastros propios y no se integran aquí. El rectángulo geográfico de entrada no garantiza cobertura del proveedor.

## Contrato de respuesta y migración desde 1.x

Cambio incompatible de contrato, manteniendo los seis nombres de herramientas:

- Leer `inmuebles[]`, `total_inmuebles`, `requiere_seleccion` y `tipo_resultado`. La lista ya no está escondida dentro de `datos_raw` ni de `mensaje_error`.
- `datos_basicos` y `direccion` de primer nivel solo se rellenan si hay un inmueble. `superficie_parcela` es el área total de la parcela, **no** la cuota de suelo atribuible a un piso.
- `estado_consulta`: `exitosa`, `sin_datos`, `requiere_seleccion`, `error_formato` o `error`. Los fallos funcionales se devuelven en este campo aunque MCP tenga `isError=false`; los errores de esquema MCP pueden tener `isError=true`.
- `codigo_error` y `errores_origen` conservan errores de Catastro. Por ejemplo, 16 significa ausencia de referencia en un punto; 76 es un parámetro de coordenadas obligatorio ausente. No se tratan igual.
- `datos_raw` es opcional. Los códigos territoriales se obtienen de la respuesta y distinguen INE y Catastro; no se deducen de referencias urbanas.
- El validador acepta códigos de parcela como utilizables; para referencias completas verifica control módulo 23. `existencia_confirmada=null` expresa que la validación local no consulta al proveedor. Las formas especiales no se fuerzan al patrón urbano/rústico. Admite espacios/guiones de presentación.
- El resumen devuelve un objeto con `resumen`, `metodo_usado`, `modelo_usado`, `motivo_degradacion` y `estado`. Si falta clave/dependencia o falla OpenAI, declara la plantilla y la causa. Los datos no permiten afirmar titularidad, valor, conservación o protección histórica.

Para un asistente que ya puede redactar, suele bastar con las herramientas de datos. El resumen se mantiene como opción; la caché evita repetir inmediatamente una consulta idéntica.

## Configuración

| Variable | Predeterminado | Uso |
|---|---|---|
| `CATASTRO_CATASTRO_BASE_URL` | `https://ovc.catastro.meh.es` | API de Catastro |
| `CATASTRO_CATASTRO_TIMEOUT` | `30` | Timeout HTTP en segundos |
| `CATASTRO_TOTAL_TIMEOUT` | `30` | Presupuesto completo por búsqueda, con cola y reintentos |
| `CATASTRO_CATASTRO_MAX_RETRIES` | `3` | Reintentos adicionales de transporte o HTTP transitorio |
| `CATASTRO_CATASTRO_RETRY_DELAY` | `1` | Espera exponencial inicial; respeta `Retry-After` dentro del presupuesto |
| `CATASTRO_MAX_CONCURRENCY` | `4` | Peticiones HTTP simultáneas por proceso |
| `CATASTRO_CACHE_TTL` | `60` | Caché de consultas, segundos; cero desactiva |
| `CATASTRO_CATALOGUE_CACHE_TTL` | `3600` | Caché de callejero, segundos |
| `CATASTRO_CACHE_SIZE` | `128` | Máximo de entradas por proceso; cero desactiva |
| `CATASTRO_REVISION` | `desconocida` | SHA del artefacto desplegado, suministrado por despliegue |
| `CATASTRO_OPENAI_API_KEY` | sin clave | Integración opcional |
| `CATASTRO_OPENAI_MODEL` | `gpt-4` | Modelo configurable |
| `CATASTRO_OPENAI_MAX_TOKENS` | `500` | Longitud máxima del resumen remoto |
| `CATASTRO_OPENAI_TEMPERATURE` | `0.3` | Parámetro del modelo configurado |
| `CATASTRO_LOG_LEVEL` | `INFO` | Logging operativo en stderr |
| `CATASTRO_LOG_SENSITIVE_DATA` | `false` | Datos sensibles solo si además el nivel es DEBUG |

Se reintentan HTTP 429/500/502/503/504 y fallos de transporte; no errores funcionales ni respuestas mal formadas. El resumen opcional dispone de un presupuesto adicional `CATASTRO_TOTAL_TIMEOUT` para OpenAI, después de consultar Catastro. La caché es local, temporal y acotada; no almacena errores del proveedor. No hay una cuota global de 60 peticiones/minuto ni caché compartida entre procesos.

## Pruebas y despliegue

```sh
uv run --locked pytest -q
uv run --locked black --check mcp_server.py smoke_catastro.py config models services tests/test_*.py
uv run --locked isort --check-only mcp_server.py smoke_catastro.py config models services tests/test_*.py
uv run --locked python smoke_catastro.py
```

`pytest` usa respuestas públicas guardadas y mocks, sin red. Los antiguos `tests/test-*.py` son scripts manuales históricos; no forman parte de la suite. `smoke_catastro.py` prueba las seis herramientas mediante un cliente MCP en memoria y llama a Catastro real; no llama a OpenAI y no se ejecuta automáticamente en CI. Se ejecuta sobre **el código local**, por lo que no certifica el conector remoto.

Tras desplegar: configurar `CATASTRO_REVISION` con el SHA, refrescar las herramientas del cliente MCP y comprobar el recurso de información remoto; repetir allí referencia, parcela única, coordenadas y dirección con/sin filtro. Esta PR no realiza el despliegue.

## Fuentes y diagnóstico

- [Contrato oficial de coordenadas WCF](https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/help/operations/Consulta_RCCOOR).
- [Contrato de dirección WCF](https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCallejero.svc/json/help/operations/consulta_dnploc).
- [Servicios libres del Catastro](https://www.catastro.hacienda.gob.es/ws/Webservices_Libres.pdf).
- [Referencia urbana y rústica](https://www.catastro.hacienda.gob.es/es-ES/referencia_catastral.html).
- [Auditoría previa a estas correcciones](docs/AUDITORIA_FUNCIONAL_2026-09-07.md).

La API puede cambiar o estar indisponible. JSON y XML se normalizan, y las respuestas inesperadas se distinguen de ausencia de datos. Licencia MIT; autor original: Pablo Cabello Hurtado.
