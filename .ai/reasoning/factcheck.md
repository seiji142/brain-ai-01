# Proceso de Factcheck

- **Consistencia interna**: decisiones coherentes con resumen y evidencia del episodio.
- **Consistencia histórica**: buscar en semántico ítems con misma entidad/proyecto/tags; detectar contradicciones.
- **Verificabilidad**: cada afirmación debe tener ≥1 evidencia concreta (url/path/excerpt).
- **Confianza**: 0-1. Hecho duplicado/apoyado +0.1; contradicción -0.3; evidencia débil -0.2.
- **Salida**: `ok(bool)`, `confidence`, `matched_semantic_ids[]`, `contradictions[]`, `actions[]` (revisar, dividir, descartar).
