# Evolución del servicio

Implementado en el contrato 2.0: búsqueda postal con callejero y selección de candidatos; coordenadas a parcela; respuestas normalizadas y errores explícitos; control de referencias; caché acotada, concurrencia y presupuesto temporal; procedencia del resumen.

Posibles ampliaciones, fuera del alcance de esta corrección:

- Integraciones específicas de catastros forales, sin confundirlas con cobertura de la DGC.
- Cuota y caché compartidas si se ejecutan varias réplicas.
- Métricas agregadas y smoke tests del conector desplegado desde infraestructura de monitorización.
- Localización por distancia como búsqueda explícita de proximidad, separada de una coincidencia en el punto.

La prioridad antes de ampliar cobertura es mantener las pruebas de contrato y la selección explícita del inmueble.
