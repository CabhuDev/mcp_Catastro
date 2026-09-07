"""
Modelos de datos para el servicio de Catastro
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ReferenciaCatastral(BaseModel):
    """Referencia normalizada; el control local no demuestra existencia."""

    referencia: str = Field(..., description="Referencia catastral completa")

    @field_validator("referencia", mode="before")
    @classmethod
    def validar_formato(cls, value: str) -> str:
        ref = cls.normalizar(value)
        analysis = cls.analizar_referencia_detallado(ref)
        if not analysis["es_referencia_completa"] or not analysis["control_valido"]:
            raise ValueError(analysis["mensaje"])
        return ref

    @staticmethod
    def normalizar(value: str) -> str:
        return re.sub(r"[\s-]", "", value).upper()

    @staticmethod
    def caracteres_control(base: str) -> str:
        """Control módulo 23; las letras siguen el alfabeto español con Ñ."""
        alphabet = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
        weights = (13, 15, 12, 5, 4, 17, 9, 21, 3, 7, 1)
        result = ""
        for start in (0, 7):
            block = base[start : start + 7] + base[14:18]
            total = sum(
                weight * (int(char) if char in "0123456789" else alphabet.index(char) + 1)
                for char, weight in zip(block, weights, strict=True)
            )
            result += "MQWERTYUIOPASDFGHJKLBZX"[total % 23]
        return result

    @classmethod
    def validar_formato_estatico(cls, referencia: str) -> bool:
        return bool(re.fullmatch(r"[0-9A-ZÑ]{14}[0-9]{4}[A-Z]{2}", cls.normalizar(referencia)))

    @classmethod
    def analizar_referencia_detallado(cls, referencia: str) -> dict:
        ref = cls.normalizar(referencia)
        complete = cls.validar_formato_estatico(ref)
        parcel = bool(re.fullmatch(r"[0-9A-ZÑ]{14}", ref))
        control = cls.caracteres_control(ref[:18]) == ref[18:] if complete else None
        kind = "desconocida"
        if complete or parcel:
            if re.fullmatch(r"[0-9]{5}[A-Z][0-9]{8}", ref[:14]):
                kind = "rustica"
            elif re.fullmatch(r"[0-9]{7}[A-ZÑ]{2}[0-9]{4}[A-ZÑ]", ref[:14]):
                kind = "urbana"
            else:
                kind = "especial_o_no_clasificada"
        valid = parcel or (complete and control is True)
        message = (
            "Código de parcela utilizable; existencia no comprobada."
            if parcel
            else (
                "Formato y caracteres de control válidos; existencia no comprobada."
                if valid
                else (
                    "Caracteres de control incorrectos."
                    if complete
                    else "Formato inválido: se requieren 14 caracteres de parcela o 20 de inmueble."
                )
            )
        )
        return {
            "referencia_original": referencia,
            "referencia_limpia": ref,
            "longitud": len(ref),
            "caracteres_validos": bool(re.fullmatch(r"[0-9A-ZÑ]+", ref)),
            "es_referencia_completa": complete,
            "es_codigo_parcela": parcel,
            "formato_valido": complete or parcel,
            "control_valido": control,
            "existencia_confirmada": None,
            "es_valida": valid,
            "tipo": kind,
            "estado": "valida" if valid else "error",
            "mensaje": message,
        }


class Coordenadas(BaseModel):
    """Coordenadas geográficas"""

    latitud: float = Field(..., ge=-90.0, le=90.0, description="Latitud en grados decimales")
    longitud: float = Field(..., ge=-180.0, le=180.0, description="Longitud en grados decimales")
    sistema: str = Field(default="WGS84", description="Sistema de coordenadas")


class DatosBasicosInmueble(BaseModel):
    """Datos básicos de un inmueble catastral"""

    uso: Optional[str] = Field(None, description="Uso del inmueble")
    superficie_construida: Optional[float] = Field(None, description="Superficie construida en m²")
    superficie_suelo: Optional[float] = Field(None, description="Superficie de suelo en m²")
    antiguedad: Optional[int] = Field(None, description="Año de construcción")
    plantas: Optional[int] = Field(None, description="Número de plantas")


class DireccionCatastral(BaseModel):
    """Dirección catastral del inmueble"""

    via: Optional[str] = Field(None, description="Tipo y nombre de vía")
    numero: Optional[str] = Field(None, description="Número")
    bloque: Optional[str] = None
    escalera: Optional[str] = None
    texto_completo: Optional[str] = None
    provincia_codigo_ine: Optional[str] = None
    municipio_codigo_ine: Optional[str] = None
    municipio_codigo_catastro: Optional[str] = None
    poligono: Optional[str] = None
    parcela_rustica: Optional[str] = None
    paraje: Optional[str] = None
    planta: Optional[str] = Field(None, description="Planta")
    puerta: Optional[str] = Field(None, description="Puerta")
    codigo_postal: Optional[str] = Field(None, description="Código postal")
    municipio: Optional[str] = Field(None, description="Municipio")
    provincia: Optional[str] = Field(None, description="Provincia")


class ValorCatastral(BaseModel):
    """Valores catastrales del inmueble"""

    valor_catastral: Optional[float] = Field(None, description="Valor catastral total")
    valor_suelo: Optional[float] = Field(None, description="Valor catastral del suelo")
    valor_construccion: Optional[float] = Field(
        None, description="Valor catastral de la construcción"
    )
    año_valor: Optional[int] = Field(None, description="Año de los valores")


class ConstruccionCatastral(BaseModel):
    uso: Optional[str] = None
    superficie: Optional[float] = None
    escalera: Optional[str] = None
    planta: Optional[str] = None
    puerta: Optional[str] = None


class InmuebleCatastral(BaseModel):
    referencia_catastral: str
    datos_basicos: DatosBasicosInmueble
    direccion: DireccionCatastral
    coeficiente_participacion: Optional[float] = None
    construcciones: list[ConstruccionCatastral] = Field(default_factory=list)


class CandidatoCallejero(BaseModel):
    tipo: str
    nombre: str
    codigo: Optional[str] = None
    tipo_via: Optional[str] = None


class CatastroResponse(BaseModel):
    """Respuesta completa de una consulta catastral"""

    referencia_catastral: str
    datos_basicos: Optional[DatosBasicosInmueble] = None
    direccion: Optional[DireccionCatastral] = None
    valores: Optional[ValorCatastral] = None
    coordenadas: Optional[Coordenadas] = None
    fecha_consulta: datetime = Field(default_factory=datetime.now)
    estado_consulta: Literal[
        "exitosa", "sin_datos", "error", "error_formato", "requiere_seleccion"
    ] = "exitosa"
    mensaje_error: Optional[str] = None
    codigo_error: Optional[str] = None
    errores_origen: list[dict[str, str]] = Field(default_factory=list)
    inmuebles: list[InmuebleCatastral] = Field(default_factory=list)
    candidatos: list[CandidatoCallejero] = Field(default_factory=list)
    total_inmuebles: int = 0
    requiere_seleccion: bool = False
    tipo_resultado: (
        Literal["inmueble", "parcela", "direccion", "localizacion", "callejero"] | None
    ) = None
    superficie_parcela: Optional[float] = Field(
        None,
        description="Superficie total de la parcela en m²; no es la cuota de suelo del inmueble",
    )
    advertencias: list[str] = Field(default_factory=list)
    datos_raw: Optional[Dict[str, Any]] = Field(None, description="Datos originales de la API")


class ConsultaPorCoordenadas(BaseModel):
    """Modelo para consultas por coordenadas"""

    latitud: float = Field(..., ge=-90.0, le=90.0)
    longitud: float = Field(..., ge=-180.0, le=180.0)
    radio_busqueda: Optional[int] = Field(default=100, description="Radio de búsqueda en metros")


class ResumenIA(BaseModel):
    """Modelo para el resumen generado por IA"""

    referencia_catastral: str
    resumen: str
    idioma: str = Field(default="es")
    modelo_usado: str = Field(default="plantilla")
    metodo_usado: str = "plantilla"
    motivo_degradacion: Optional[str] = None
    estado: str = "exitosa"
    codigo_error: Optional[str] = None
    fecha_generacion: datetime = Field(default_factory=datetime.now)
    puntos_clave: Optional[List[str]] = None
    calidad_datos: Optional[str] = None


class ErrorCatastral(BaseModel):
    """Modelo para errores del servicio catastral"""

    codigo_error: str
    mensaje: str
    detalles: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class EstadisticasConsulta(BaseModel):
    """Estadísticas de consultas realizadas"""

    total_consultas: int = 0
    consultas_exitosas: int = 0
    consultas_fallidas: int = 0
    tiempo_promedio_respuesta: float = 0.0
    fecha_inicio: datetime = Field(default_factory=datetime.now)
    ultima_consulta: Optional[datetime] = None
