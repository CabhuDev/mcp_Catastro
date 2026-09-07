# Guía de uso del contrato 2.0

La referencia vigente de herramientas, parámetros, estados y configuración está en el [README](../README.md).

1. Si se conoce la referencia completa, consultar el inmueble directamente. El validador comprueba formato y control, pero no existencia.
2. Si se conoce dirección, usar provincia, municipio, tipo/nombre de vía y número. Elegir un candidato cuando el callejero resulte ambiguo; añadir escalera/planta/puerta para concretar.
3. Si se conoce un punto, consultar coordenadas y seleccionar un inmueble de la parcela. No inferir que el primer resultado es la vivienda buscada.
4. Leer `estado_consulta` y `codigo_error` antes de utilizar datos. `sin_datos` no es lo mismo que error de entrada, conexión o proveedor.
5. Usar `incluir_raw` solo para diagnóstico; la información normalizada se encuentra en `inmuebles`.
6. Para resumir, usar el asistente o `generar_resumen_ia`; este último declara si ha utilizado una plantilla o OpenAI.

La guía anterior describía el comportamiento de la versión antigua; los ejemplos y el contrato actualizado están centralizados para evitar contradicciones.
