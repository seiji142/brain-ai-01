# Uso de herramientas (MCP)

- `ingest(episode_json)`: valida schema, redacta PII, guarda episodic, indexa episodic (opcional), devuelve episode_id/trace_id.
- `retrieve(query, filters)`: devuelve top_k con score/evidencia/trace_id.
- `consolidate(scope)`: corre consolidación (proyecto o global), devuelve resumen de promociones/contradicciones/trace_id.
- `evaluate(query, filters)`: ejecuta retrieve+evaluación, guarda logs/evaluations, devuelve métricas agregadas.
- `factcheck(statement_or_episode_id)`: devuelve veredicto + confianza + evidencias + contradicciones.
