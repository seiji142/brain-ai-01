# Reglas operativas

- No almacenar PII sensible (passwords, tokens, DNI, tarjetas). Si aparece, enmascarar como [REDACTED].
- Todo episodio debe incluir: id, project, timestamp (ISO8601 UTC), source_type, author, decisions[], evidence[], tags[].
- Todo ítem semántico debe incluir: id, type (fact/decision/pattern/mistake), statement, confidence (0-1), evidence_source_ids[], contradictions[], created_at, updated_at.
- Consolidación: solo promover a semántico si confidence >= 0.6 y al menos 1 evidencia verificable.
- Retrieval: siempre devolver top_k con score, filtros aplicados, y trace_id.
- Evaluación: registrar relevance (0-1), has_evidence (bool), hallucination_risk (0-1), notes.
