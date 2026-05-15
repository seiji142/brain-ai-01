# Sistema de Memoria y Aprendizaje

Objetivos:
- Persistencia de conocimiento (episódico + semántico + resúmenes + reflexiones)
- Recuperación eficiente híbrida (vectorial + metadatos + scoring + filtros)
- Consolidación/aprendizaje (ingest → resumen → reflexión → promoción a semántico → re-index)
- Gobernanza/confianza (políticas, trazabilidad, factcheck, evaluación, logs auditables)
- Compatibilidad multi-modelo (módulos Python reutilizables + MCP server + archivos versionables)
- Separación episódica/semántica explícita

Principios:
1. Toda unidad de conocimiento referencia evidencia (source_ids).
2. Todo retrieval devuelve score + evidencia + trazabilidad (trace_id).
3. Toda promoción a semántico requiere factcheck mínimo (fuente, consistencia, contradicción).
4. Todo evento se audita en logs/traces y logs/evaluations.
