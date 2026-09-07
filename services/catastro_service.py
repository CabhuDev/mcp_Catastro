"""Consultas públicas al Catastro y normalización de sus respuestas WCF/ASMX."""

import asyncio
import json
import logging
import math
import re
import time
import unicodedata
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import wraps
from typing import Any

import httpx
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from pydantic import ValidationError

from config.settings import (
    CatastroEndpoints,
    get_settings,
    log_failure,
)
from models.catastro_models import (
    CandidatoCallejero,
    CatastroResponse,
    ConstruccionCatastral,
    Coordenadas,
    DatosBasicosInmueble,
    DireccionCatastral,
    InmuebleCatastral,
    ReferenciaCatastral,
)

logger = logging.getLogger(__name__)


def as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def number(value: Any) -> float | None:
    """Catastro usa punto de miles y coma decimal en los listados."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if re.fullmatch(r"-?[0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]+)?", text):
        text = text.replace(".", "")
    value = float(text.replace(",", "."))
    if not math.isfinite(value):
        raise ValueError("Número no finito en la respuesta del Catastro")
    return value


def query_budget(method):
    """Incluye espera de concurrencia, reintentos y consultas encadenadas."""

    @wraps(method)
    async def bounded(self, *args, **kwargs):
        try:
            async with asyncio.timeout(self.settings.catastro_total_timeout):
                return await method(self, *args, **kwargs)
        except TimeoutError as exc:
            ref = kwargs.get(
                "referencia", kwargs.get("codigo_parcela", args[0] if args else "DESCONOCIDA")
            )
            return self._error(ref if isinstance(ref, str) else "DESCONOCIDA", exc)

    return bounded


class CatastroService:
    def __init__(self, http_client: httpx.AsyncClient | None = None):
        self.settings = get_settings()
        self.base_url = self.settings.catastro_base_url
        self.timeout = self.settings.catastro_timeout
        self.max_retries = self.settings.catastro_max_retries
        self.retry_delay = self.settings.catastro_retry_delay
        self.http_client = http_client or httpx.AsyncClient(timeout=self.timeout)
        self._owns_http_client = http_client is None
        self._semaphore = asyncio.Semaphore(self.settings.catastro_max_concurrency)
        self._cache: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self.http_client.aclose()

    def _error(self, referencia: str, exc: Exception) -> CatastroResponse:
        log_failure(
            logger,
            logging.ERROR,
            self.settings.log_sensitive_data,
            "Error consultando Catastro",
            exc,
        )
        invalid = isinstance(exc, ValidationError)
        timeout = isinstance(exc, (TimeoutError, httpx.TimeoutException))
        if isinstance(exc, httpx.HTTPStatusError):
            return CatastroResponse(
                referencia_catastral=referencia,
                estado_consulta="error",
                codigo_error=f"HTTP_{exc.response.status_code}",
                mensaje_error=f"Catastro devolvió HTTP {exc.response.status_code}",
            )
        if isinstance(exc, httpx.TransportError) and not timeout:
            return CatastroResponse(
                referencia_catastral=referencia,
                estado_consulta="error",
                codigo_error="ERROR_CONEXION",
                mensaje_error="No se pudo conectar con Catastro",
            )
        return CatastroResponse(
            referencia_catastral=referencia,
            estado_consulta="error_formato" if invalid else "error",
            codigo_error=(
                "ENTRADA_INVALIDA"
                if invalid
                else (
                    "TIMEOUT"
                    if timeout
                    else "RESPUESTA_INVALIDA" if isinstance(exc, ValueError) else "ERROR_SERVICIO"
                )
            ),
            mensaje_error=(
                "Entrada inválida"
                if invalid
                else "Tiempo de consulta agotado" if timeout else str(exc)
            ),
        )

    @query_budget
    async def consultar_por_referencia(
        self, referencia: str, incluir_raw: bool = False
    ) -> CatastroResponse:
        try:
            ref = ReferenciaCatastral(referencia=referencia).referencia
            return await self._consultar_referencia(ref, "inmueble", incluir_raw)
        except Exception as exc:
            return self._error(referencia, exc)

    @query_budget
    async def consultar_parcela_por_codigo(
        self, codigo_parcela: str, incluir_raw: bool = False
    ) -> CatastroResponse:
        ref = ReferenciaCatastral.normalizar(codigo_parcela)
        if not ReferenciaCatastral.analizar_referencia_detallado(ref)["es_codigo_parcela"]:
            return CatastroResponse(
                referencia_catastral=ref,
                estado_consulta="error_formato",
                codigo_error="ENTRADA_INVALIDA",
                mensaje_error="Código de parcela inválido",
            )
        try:
            return await self._consultar_referencia(ref, "parcela", incluir_raw)
        except Exception as exc:
            return self._error(ref, exc)

    async def _consultar_referencia(
        self, ref: str, kind: str, incluir_raw: bool
    ) -> CatastroResponse:
        raw = await self._request(
            CatastroEndpoints.CONSULTA_DNPRC, {"Provincia": "", "Municipio": "", "RefCat": ref}
        )
        return self._construir_respuesta_catastral(ref, raw, kind, incluir_raw)

    async def _request(self, endpoint: str, params: dict[str, str]) -> dict:
        key = (endpoint, tuple(sorted(params.items())))
        cached = self._cache.get(key)
        if cached and cached[0] > time.monotonic():
            self._cache.move_to_end(key)
            logger.info("Caché Catastro endpoint=%s", endpoint.rsplit("/", 1)[-1])
            return deepcopy(cached[1])
        if cached:
            del self._cache[key]
        response = await self._realizar_consulta_con_reintentos(self.base_url + endpoint, params)
        raw = self._parsear_respuesta_json(response.text)
        root = self._root(raw)
        ttl = (
            self.settings.catastro_catalogue_cache_ttl
            if "Obtener" in endpoint
            else self.settings.catastro_cache_ttl
        )
        if ttl > 0 and self.settings.catastro_cache_size > 0 and not self._provider_error(root, ""):
            self._cache[key] = (time.monotonic() + ttl, deepcopy(raw))
            self._cache.move_to_end(key)
            while len(self._cache) > self.settings.catastro_cache_size:
                self._cache.popitem(last=False)
        return raw

    def _parsear_respuesta_json(self, content: str) -> dict:
        try:
            data = json.loads(content.lstrip("\ufeff"))
        except json.JSONDecodeError:
            return self._parsear_respuesta_xml(content)
        if not isinstance(data, dict):
            raise ValueError("Respuesta JSON inesperada del Catastro")
        return data

    def _parsear_respuesta_xml(self, content: str) -> dict:
        try:
            root = ET.fromstring(content)
            if root.tag.rsplit("}", 1)[-1].lower() not in {"consulta_dnp", "consulta_coordenadas"}:
                raise ValueError("Error parseando respuesta: raíz XML inesperada")
            return self._xml_a_dict(root)
        except (ET.ParseError, DefusedXmlException) as exc:
            raise ValueError("Error parseando respuesta del Catastro") from exc

    def _xml_a_dict(self, element) -> Any:
        if not len(element):
            return element.text.strip() if element.text and element.text.strip() else {}
        result: dict = {}
        for child in element:
            key = child.tag.rsplit("}", 1)[-1]
            value = self._xml_a_dict(child)
            if key in result:
                result[key] = as_list(result[key]) + [value]
            else:
                result[key] = value
        return result

    @staticmethod
    def _root(raw: dict) -> dict:
        wrapped = [value for key, value in raw.items() if key.lower().endswith("result")]
        root = wrapped[0] if len(wrapped) == 1 else raw
        if not isinstance(root, dict) or not any(
            key in root for key in ("control", "bico", "lrcdnp", "coordenadas", "lerr")
        ):
            raise ValueError("Estructura de respuesta del Catastro no reconocida")
        control = root.get("control", {})
        if not isinstance(control, dict):
            raise ValueError("Control de respuesta inválido")
        if not root.get("lerr") and not int(control.get("cuerr", 0)):
            for count, containers in {
                "cudnp": ("bico", "lrcdnp"),
                "cucoor": ("coordenadas",),
                "cumun": ("municipiero",),
                "cuca": ("callejero",),
            }.items():
                if int(control.get(count, 0)) > 0 and not any(root.get(key) for key in containers):
                    raise ValueError("Catastro anuncia resultados pero falta su contenido")
        return root

    def _provider_error(self, root: dict, ref: str) -> CatastroResponse | None:
        errors = root.get("lerr")
        if isinstance(errors, dict):
            errors = errors.get("err", errors)
        errors = [
            {
                "codigo": str(e.get("cod", "DESCONOCIDO")),
                "mensaje": str(e.get("des", "Error del Catastro")),
            }
            for e in as_list(errors)
        ]
        if not errors and int(root.get("control", {}).get("cuerr", 0)) > 0:
            errors = [
                {"codigo": "DESCONOCIDO", "mensaje": "Catastro informó de un error sin detalle"}
            ]
        if not errors:
            return None
        codes = {error["codigo"] for error in errors}
        status = (
            "sin_datos"
            if codes <= {"5", "16"}
            else "error_formato" if codes <= {"4", "76", "77"} else "error"
        )
        return CatastroResponse(
            referencia_catastral=ref,
            estado_consulta=status,
            codigo_error=errors[0]["codigo"],
            errores_origen=errors,
            mensaje_error="; ".join(error["mensaje"] for error in errors),
        )

    def _construir_respuesta_catastral(
        self, referencia: str, datos_raw: dict, kind: str = "inmueble", incluir_raw: bool = False
    ) -> CatastroResponse:
        try:
            root = self._root(datos_raw)
            failure = self._provider_error(root, referencia)
            if failure:
                failure.datos_raw = datos_raw if incluir_raw else None
                return failure
            if root.get("bico"):
                bico = root["bico"]
                items = [self._inmueble(bico["bi"], bico)]
            elif root.get("lrcdnp"):
                items = [self._inmueble(item) for item in as_list(root["lrcdnp"].get("rcdnp"))]
            elif int(root.get("control", {}).get("cudnp", 0)) > 0:
                raise ValueError("Respuesta con inmuebles pero sin datos reconocibles")
            else:
                items = []
            individual = items[0] if len(items) == 1 else None
            result = CatastroResponse(
                referencia_catastral=referencia,
                estado_consulta="exitosa" if items else "sin_datos",
                superficie_parcela=number(
                    root.get("bico", {}).get("finca", {}).get("dff", {}).get("ss")
                ),
                tipo_resultado=kind,
                inmuebles=items,
                total_inmuebles=len(items),
                requiere_seleccion=len(items) > 1,
                datos_basicos=individual.datos_basicos if individual else None,
                direccion=individual.direccion if individual else None,
                datos_raw=datos_raw if incluir_raw else None,
            )
            expected = int(root.get("control", {}).get("cudnp", len(items)))
            if expected != len(items):
                result.advertencias.append(
                    f"Catastro anuncia {expected} inmuebles; se recibieron {len(items)}"
                )
            return result
        except Exception as exc:
            result = self._error(referencia, exc)
            result.codigo_error = "RESPUESTA_INVALIDA"
            result.datos_raw = datos_raw if incluir_raw else None
            return result

    @staticmethod
    def _inmueble(bi: dict, bico: dict | None = None) -> InmuebleCatastral:
        bico = bico or {}
        rc = bi.get("rc") or bi.get("idbi", {}).get("rc", {})
        reference = "".join(str(rc.get(key, "")) for key in ("pc1", "pc2", "car", "cc1", "cc2"))
        if not ReferenciaCatastral.validar_formato_estatico(reference):
            raise ValueError("Inmueble sin referencia completa en la respuesta")
        dt = bi.get("dt", {})
        locs = dt.get("locs", {})
        location = locs.get("lous") or locs.get("lors") or {}
        urban = location.get("lourb", {})
        rural = location.get("lorus", {})
        road, interior = urban.get("dir", {}), urban.get("loint", {})
        ine = dt.get("loine", {})

        def optional(value):
            return str(value).strip() if value is not None and value != "" else None

        street = " ".join(str(road.get(k, "")) for k in ("tv", "nv")).strip() or None
        address = DireccionCatastral(
            via=street,
            numero=optional(road.get("pnp")),
            bloque=optional(road.get("bq")),
            escalera=optional(interior.get("es")),
            planta=optional(interior.get("pt")),
            puerta=optional(interior.get("pu")),
            codigo_postal=optional(urban.get("dp")),
            texto_completo=optional(bi.get("ldt")),
            municipio=optional(dt.get("nm")),
            provincia=optional(dt.get("np")),
            provincia_codigo_ine=optional(ine.get("cp")),
            municipio_codigo_ine=optional(ine.get("cm")),
            municipio_codigo_catastro=optional(dt.get("cmc")),
            poligono=optional(rural.get("cpp", {}).get("cpo")),
            parcela_rustica=optional(rural.get("cpp", {}).get("cpa")),
            paraje=optional(rural.get("npa")),
        )
        debi = bi.get("debi", {})
        data = DatosBasicosInmueble(
            uso=debi.get("luso"),
            superficie_construida=number(debi.get("sfc")),
            antiguedad=int(debi["ant"]) if debi.get("ant") else None,
        )
        constructions = bico.get("lcons")
        if isinstance(constructions, dict):
            constructions = constructions.get("cons", constructions)
        parts = []
        for part in as_list(constructions):
            interior = part.get("dt", {}).get("lourb", {}).get("loint", {})
            parts.append(
                ConstruccionCatastral(
                    uso=part.get("lcd"),
                    superficie=number(part.get("dfcons", {}).get("stl")),
                    escalera=optional(interior.get("es")),
                    planta=optional(interior.get("pt")),
                    puerta=optional(interior.get("pu")),
                )
            )
        return InmuebleCatastral(
            referencia_catastral=reference,
            datos_basicos=data,
            direccion=address,
            coeficiente_participacion=number(debi.get("cpt")),
            construcciones=parts,
        )

    async def _realizar_consulta_con_reintentos(
        self,
        url: str,
        params: dict[str, str],
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Reintenta solo transporte y estados transitorios, dentro del presupuesto."""
        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            response = None
            try:
                async with self._semaphore:
                    response = await self.http_client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                if not response.text.strip():
                    raise ValueError("Respuesta vacía del Catastro")
                logger.info(
                    "Consulta Catastro endpoint=%s estado=%d duracion_ms=%.1f intento=%d",
                    url.rsplit("/", 1)[-1],
                    response.status_code,
                    (time.monotonic() - start) * 1000,
                    attempt + 1,
                )
                return response
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                retryable = isinstance(exc, httpx.TransportError) or exc.response.status_code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }
                if not retryable or attempt == self.max_retries:
                    raise
                delay = self.retry_delay * (2**attempt)
                if response is not None and response.headers.get("Retry-After"):
                    delay = max(delay, self._retry_after(response.headers["Retry-After"]))
                logger.warning(
                    "Reintento Catastro endpoint=%s intento=%d", url.rsplit("/", 1)[-1], attempt + 1
                )
                await asyncio.sleep(delay)
        raise RuntimeError("Consulta sin resultado")

    @staticmethod
    def _retry_after(value: str) -> float:
        try:
            return max(0, float(value))
        except ValueError:
            try:
                return max(
                    0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
                )
            except ValueError, TypeError, OverflowError:
                return 0

    @query_budget
    async def consultar_por_coordenadas(
        self, latitud: float, longitud: float, incluir_raw: bool = False
    ) -> CatastroResponse:
        """Localiza parcelas; las coordenadas no identifican una planta/puerta."""
        try:
            coords = Coordenadas(latitud=latitud, longitud=longitud)
            if not (27 <= coords.latitud <= 44 and -19 <= coords.longitud <= 5):
                return CatastroResponse(
                    referencia_catastral="DESCONOCIDA",
                    coordenadas=coords,
                    estado_consulta="error",
                    codigo_error="FUERA_COBERTURA",
                    mensaje_error="Punto fuera del ámbito geográfico admitido por este conector de Catastro",
                )
            raw = await self._request(
                CatastroEndpoints.CONSULTA_RCCOOR,
                {"SRS": "EPSG:4326", "CoorX": str(coords.longitud), "CoorY": str(coords.latitud)},
            )
            root = self._root(raw)
            failure = self._provider_error(root, "DESCONOCIDA")
            if failure:
                failure.coordenadas = coords
                failure.datos_raw = raw if incluir_raw else None
                return failure
            references = self._extraer_referencias_de_coordenadas(root)
            if not references:
                raise ValueError("Respuesta de coordenadas sin parcelas reconocibles")
            parcels = [
                await self.consultar_parcela_por_codigo(ref, incluir_raw) for ref in references
            ]
            failed = [p for p in parcels if p.estado_consulta != "exitosa"]
            if failed:
                result = failed[0]
                result.coordenadas = coords
                result.advertencias.append(
                    "No se pudo completar la consulta de todas las parcelas localizadas"
                )
                return result
            if len(parcels) == 1:
                result = parcels[0]
            else:
                items = {i.referencia_catastral: i for p in parcels for i in p.inmuebles}
                result = CatastroResponse(
                    referencia_catastral="BUSQUEDA_COORDENADAS",
                    inmuebles=list(items.values()),
                    total_inmuebles=len(items),
                    requiere_seleccion=len(items) > 1,
                )
            result.tipo_resultado = "localizacion"
            result.coordenadas = coords
            result.advertencias.append(
                "Las coordenadas localizan la parcela; seleccione el inmueble por escalera, planta y puerta"
            )
            if incluir_raw:
                result.datos_raw = {"coordenadas": raw, "parcelas": [p.datos_raw for p in parcels]}
            return result
        except Exception as exc:
            return self._error("DESCONOCIDA", exc)

    @staticmethod
    def _extraer_referencias_de_coordenadas(root: dict) -> list[str]:
        references = []
        for coord in as_list(root.get("coordenadas", {}).get("coord")):
            pc = coord.get("pc", {})
            reference = str(pc.get("pc1", "")) + str(pc.get("pc2", ""))
            if not ReferenciaCatastral.analizar_referencia_detallado(reference)[
                "es_codigo_parcela"
            ]:
                raise ValueError("Código de parcela inválido en respuesta de coordenadas")
            if reference not in references:
                references.append(reference)
        return references

    @query_budget
    async def buscar_por_direccion(
        self,
        provincia: str,
        municipio: str,
        tipo_via: str = "",
        nombre_via: str = "",
        numero: str = "",
        direccion_original: str = "",
        bloque: str = "",
        escalera: str = "",
        planta: str = "",
        puerta: str = "",
        incluir_raw: bool = False,
    ) -> CatastroResponse:
        """Resuelve nombres oficiales antes de consultar una dirección."""
        logger.info("Búsqueda por dirección solicitada")
        if not all(value.strip() for value in (provincia, municipio, nombre_via)):
            return CatastroResponse(
                referencia_catastral="BUSQUEDA_DIRECCION",
                estado_consulta="error_formato",
                codigo_error="ENTRADA_INVALIDA",
                mensaje_error="Indique provincia, municipio y nombre de vía",
            )
        try:
            raw = await self._request(
                CatastroEndpoints.CONSULTA_MUNICIPIO,
                {"Provincia": provincia, "Municipio": municipio},
            )
            root = self._root(raw)
            failure = self._provider_error(root, "BUSQUEDA_DIRECCION")
            if failure:
                failure.datos_raw = raw if incluir_raw else None
                return failure
            municipalities = [
                CandidatoCallejero(
                    tipo="municipio", nombre=m["nm"], codigo=str(m.get("locat", {}).get("cmc", ""))
                )
                for m in as_list(root.get("municipiero", {}).get("muni"))
            ]
            selected = self._select_candidate(municipalities, municipio)
            if selected is None:
                return self._candidates(
                    municipalities,
                    "Seleccione un municipio del callejero oficial",
                    raw if incluir_raw else None,
                )
            municipio = selected.nombre
            types = {
                "CALLE": "CL",
                "AVENIDA": "AV",
                "PLAZA": "PZ",
                "PASEO": "PS",
                "CARRETERA": "CR",
                "CAMINO": "CM",
                "TRAVESIA": "TR",
                "GLORIETA": "GL",
            }
            tipo_via = types.get(self._canonical(tipo_via), tipo_via.upper())
            raw = await self._request(
                CatastroEndpoints.CONSULTA_VIA,
                {
                    "Provincia": provincia,
                    "Municipio": municipio,
                    "TipoVia": tipo_via,
                    "NomVia": nombre_via,
                },
            )
            root = self._root(raw)
            failure = self._provider_error(root, "BUSQUEDA_DIRECCION")
            if failure:
                failure.datos_raw = raw if incluir_raw else None
                return failure
            streets = [
                CandidatoCallejero(
                    tipo="via",
                    nombre=c["dir"]["nv"],
                    codigo=str(c["dir"].get("cv", "")),
                    tipo_via=c["dir"].get("tv"),
                )
                for c in as_list(root.get("callejero", {}).get("calle"))
            ]
            selected = self._select_candidate(streets, nombre_via)
            if selected is None:
                return self._candidates(
                    streets,
                    "Seleccione una vía y su tipo del callejero oficial",
                    raw if incluir_raw else None,
                )
            if not numero.strip():
                return self._candidates(
                    [selected],
                    "Indique el número de la vía seleccionada; puede usar S/N",
                    raw if incluir_raw else None,
                )
            raw = await self._request(
                CatastroEndpoints.CONSULTA_DNPLOC,
                {
                    "Provincia": provincia,
                    "Municipio": municipio,
                    "Sigla": selected.tipo_via or "",
                    "Calle": selected.nombre,
                    "Numero": numero,
                    "Bloque": bloque,
                    "Escalera": escalera,
                    "Planta": planta,
                    "Puerta": puerta,
                },
            )
            result = self._construir_respuesta_catastral(
                "BUSQUEDA_DIRECCION", raw, "direccion", incluir_raw
            )
            if result.total_inmuebles == 1:
                result.referencia_catastral = result.inmuebles[0].referencia_catastral
            return result
        except Exception as exc:
            return self._error("BUSQUEDA_DIRECCION", exc)

    @staticmethod
    def _canonical(value: str) -> str:
        return " ".join(
            "".join(
                c
                for c in unicodedata.normalize("NFD", value.upper())
                if not unicodedata.combining(c)
            ).split()
        )

    @classmethod
    def _select_candidate(
        cls, candidates: list[CandidatoCallejero], name: str
    ) -> CandidatoCallejero | None:
        exact = [c for c in candidates if cls._canonical(c.nombre) == cls._canonical(name)]
        choices = exact or candidates
        return choices[0] if len(choices) == 1 else None

    @staticmethod
    def _candidates(
        candidates: list[CandidatoCallejero], message: str, raw: dict | None = None
    ) -> CatastroResponse:
        return CatastroResponse(
            referencia_catastral="BUSQUEDA_DIRECCION",
            tipo_resultado="callejero",
            estado_consulta="requiere_seleccion" if candidates else "sin_datos",
            candidatos=candidates,
            requiere_seleccion=bool(candidates),
            advertencias=[message],
            datos_raw=raw,
        )
