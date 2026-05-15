# Evaluación

Métricas por retrieve:
- **Relevance** (0-1): ¿responde la intención de la query?
- **Has_evidence** (bool): ¿incluye evidencia verificable?
- **Hallucination_risk** (0-1): contradicciones, afirmaciones sin fuente, ambigüedad.
- **Recall@k / Precision@k** (cuando hay ground truth).
- **Time-to-answer** (latencia) y **coste** (si embeddings pagas).

Registro: `logs/evaluations/*.jsonl` con `trace_id`, `query`, `retrieved_ids`, `scores`, `relevance`, `has_evidence`, `hallucination_risk`, `notes`.
