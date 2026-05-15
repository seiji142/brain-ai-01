#!/usr/bin/env python3
"""Genera el manual PDF del Sistema de Memoria y Aprendizaje"""

from fpdf import FPDF
from pathlib import Path
import datetime

OUTPUT = Path(__file__).parent.parent / "MANUAL_SISTEMA_MEMORIA.pdf"
ARIAL = "C:/Windows/Fonts/arial.ttf"
ARIAL_BD = "C:/Windows/Fonts/arialbd.ttf"
ARIAL_BI = "C:/Windows/Fonts/arialbi.ttf"
ARIAL_I = "C:/Windows/Fonts/ariali.ttf"
COURIER = "C:/Windows/Fonts/cour.ttf"
COURIER_BD = "C:/Windows/Fonts/courbd.ttf"


class ManualPDF(FPDF):
    def __init__(self):
        super().__init__("P", "mm", "A4")
        self.set_auto_page_break(auto=True, margin=25)
        self.add_font("ArialUni", "", ARIAL)
        self.add_font("ArialUni", "B", ARIAL_BD)
        self.add_font("ArialUni", "I", ARIAL_I)
        self.add_font("ArialUni", "BI", ARIAL_BI)
        self.add_font("CourierNew", "", COURIER)
        self.add_font("CourierNew", "B", COURIER_BD)

    def header(self):
        if self.page_no() > 1:
            self.set_font("ArialUni", "B", 8)
            self.set_text_color(120, 120, 120)
            self.cell(0, 4, "Sistema de Memoria y Aprendizaje - Manual v1.0", align="L")
            self.cell(0, 4, f"Pag. {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
            self.set_draw_color(200, 200, 200)
            self.line(10, 12, 200, 12)
            self.ln(4)

    def footer(self):
        if self.page_no() > 1:
            self.set_y(-15)
            self.set_font("ArialUni", "", 7)
            self.set_text_color(160, 160, 160)
            self.cell(0, 10, "brain-ai-01  |  " + datetime.datetime.now().strftime("%Y-%m-%d"), align="C")

    def titulo(self, text, size=24):
        self.set_font("ArialUni", "B", size)
        self.set_text_color(20, 60, 120)
        self.cell(0, 14, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(20, 60, 120)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def subtitulo(self, text, size=14):
        self.set_font("ArialUni", "B", size)
        self.set_text_color(40, 90, 160)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(100, 150, 210)
        self.line(10, self.get_y(), 100, self.get_y())
        self.ln(2)

    def sub_subtitulo(self, text, size=11):
        self.set_font("ArialUni", "B", size)
        self.set_text_color(60, 60, 60)
        self.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def parrafo(self, text, size=10):
        self.set_font("ArialUni", "", size)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def bullet(self, text, size=10):
        self.set_font("ArialUni", "", size)
        self.set_text_color(40, 40, 40)
        self.cell(6, 5.5, "-")
        self.multi_cell(174, 5.5, text)

    def code_block(self, text, size=7.5):
        self.set_fill_color(245, 245, 250)
        self.set_draw_color(200, 200, 210)
        self.set_font("CourierNew", "", size)
        self.set_text_color(30, 30, 40)
        lines = text.split("\n")
        block_h = len(lines) * 4 + 4
        if self.get_y() + block_h > 270:
            self.add_page()
        y_start = self.get_y()
        self.rect(10, y_start, 190, block_h, style="DF")
        self.set_xy(12, y_start + 2)
        for line in lines:
            self.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
            self.set_x(12)
        self.ln(3)

    def table(self, headers, rows, col_widths=None):
        if col_widths is None:
            col_widths = [190 / len(headers)] * len(headers)
        self.set_font("ArialUni", "B", 9)
        self.set_fill_color(20, 60, 120)
        self.set_text_color(255, 255, 255)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()
        self.set_font("ArialUni", "", 9)
        for ri, row in enumerate(rows):
            if ri % 2 == 0:
                self.set_fill_color(248, 248, 252)
            else:
                self.set_fill_color(255, 255, 255)
            self.set_text_color(40, 40, 40)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6.5, str(cell), border=1, fill=True, align="C" if i > 0 else "L")
            self.ln()
        self.ln(2)

    def note_box(self, text, icon="!"):
        self.set_fill_color(235, 245, 255)
        self.set_draw_color(100, 150, 210)
        y = self.get_y()
        self.set_font("ArialUni", "B", 14)
        self.set_text_color(20, 60, 120)
        self.cell(8, 7, icon)
        self.set_font("ArialUni", "", 9)
        self.set_text_color(40, 60, 100)
        self.multi_cell(0, 5, text)
        self.set_draw_color(100, 150, 210)
        self.line(10, y, 200, y)
        self.ln(2)


def build():
    pdf = ManualPDF()

    # ---- PORTADA ----
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("ArialUni", "B", 36)
    pdf.set_text_color(20, 60, 120)
    pdf.cell(0, 12, "Sistema de Memoria", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 12, "y Aprendizaje", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("ArialUni", "", 18)
    pdf.set_text_color(80, 120, 180)
    pdf.cell(0, 10, "Capa cognitiva persistente para agentes de IA", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_draw_color(20, 60, 120)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(10)
    pdf.set_font("ArialUni", "", 11)
    pdf.set_text_color(100, 100, 100)
    now = datetime.datetime.now()
    pdf.cell(0, 7, "Version 1.0  |  " + now.strftime("%B %Y"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "Proyecto: brain-ai-01", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(40)
    pdf.set_font("ArialUni", "", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.cell(0, 5, "Basado en: Artemis v3, GPT-5, MinMax-M2.7", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Stack: Python  |  ChromaDB  |  FastAPI  |  Pydantic", align="C", new_x="LMARGIN", new_y="NEXT")

    # ---- INDICE ----
    pdf.add_page()
    pdf.titulo("Indice", 20)
    pdf.ln(2)
    toc = [
        ("1", "Proposito"),
        ("2", "Arquitectura de Memoria"),
        ("  2.1", "Memoria Episodica"),
        ("  2.2", "Memoria Semantica"),
        ("  2.3", "Sistema de Recuperacion"),
        ("3", "Ciclo de Aprendizaje"),
        ("4", "Scoring Hibrido"),
        ("5", "APIs MCP (FastAPI)"),
        ("6", "Mejoras Futuras"),
        ("7", "Estructura de Datos"),
        ("8", "Comandos de Uso"),
    ]
    for num, title in toc:
        b = "B" if not num.startswith(" ") else ""
        pdf.set_font("ArialUni", b, 10)
        pdf.set_text_color(40, 40, 40)
        indent = 12 if num.startswith(" ") else 0
        pdf.set_x(12 + indent)
        pdf.cell(10, 6, num.strip(), align="R")
        pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")

    # ---- SECCION 1 ----
    pdf.add_page()
    pdf.titulo("1. Proposito")
    pdf.parrafo(
        "Este sistema es una capa cognitiva persistente que se situa encima de cualquier LLM. "
        "No es un 'chatbot con memoria', sino un motor de aprendizaje continuo que permite que "
        "un agente de IA acumule experiencia, la consolide en conocimiento reutilizable, y "
        "mejore con el tiempo independientemente del modelo subyacente."
    )
    pdf.parrafo("Resuelve cinco problemas fundamentales de forma simultanea:")
    pdf.table(
        ["Problema", "Solucion"],
        [
            ["Persistencia", "Datos en JSON + ChromaDB vectorial"],
            ["Recuperacion eficiente", "Busqueda hibrida (vectores + metadatos + scoring)"],
            ["Consolidacion / aprendizaje", "Episodios -> Resumen -> Factcheck -> Semantico"],
            ["Gobernanza / confianza", "Trazabilidad, politicas, redaccion PII, evaluaciones"],
            ["Compatibilidad multi-modelo", "FastAPI MCP, compatible con OpenCode/Claude/Cursor"],
        ],
        [55, 135]
    )

    # ---- SECCION 2 ----
    pdf.add_page()
    pdf.titulo("2. Arquitectura de Memoria")
    pdf.parrafo(
        "El sistema implementa tres niveles de memoria, inspirados en el modelo cognitivo "
        "humano. Cada nivel tiene un proposito, ciclo de vida y mecanismo de persistencia "
        "especifico."
    )
    pdf.subtitulo("2.1 Memoria Episodica (experiencias crudas)")
    pdf.parrafo(
        "La memoria episodica registra eventos, decisiones, acciones y resultados tal como "
        "ocurren. Es la materia prima del sistema."
    )
    pdf.bullet("Ubicacion: memory/episodic/*.json")
    pdf.bullet("Indexada en ChromaDB (coleccion episodic) para busqueda vectorial")
    pdf.bullet("Ciclo de vida: 24 meses (politica de retencion)")
    pdf.bullet("Campos: id, project, timestamp, source_type, author, title, summary, decisions, actions, risks, evidence, tags")
    pdf.subtitulo("2.2 Memoria Semantica (conocimiento consolidado)")
    pdf.parrafo(
        "Almacena conocimiento destilado y validado: hechos, decisiones importantes, "
        "patrones recurrentes y errores aprendidos."
    )
    pdf.bullet("Ubicacion: memory/semantic/*.json")
    pdf.bullet("Indexada en ChromaDB (coleccion semantic)")
    pdf.bullet("Ciclo de vida: indefinido")
    pdf.bullet("Tipos: fact, decision, pattern, mistake")
    pdf.bullet("Cada item tiene confidence score (0-1) y referencias a sus fuentes")
    pdf.subtitulo("2.3 Sistema de Recuperacion (Retrieval)")
    pdf.parrafo("Combina busqueda vectorial con filtros de metadatos y scoring hibrido.")
    pdf.bullet("Embedding: hash determinista offline (1536d) u OpenAI API")
    pdf.bullet("Filtros: proyecto, tags, rango de fechas")
    pdf.bullet("Scoring hibrido: combina similitud coseno, recencia, evidencia y confianza")
    pdf.bullet("Siempre devuelve trace_id para auditoria")
    pdf.ln(2)
    pdf.code_block(
        "+----------------------------------------------------------+\n"
        "|               SISTEMA DE MEMORIA (3 niveles)              |\n"
        "+----------------------------------------------------------+\n"
        "|  MEMORIA EPISODICA (experiencias crudas)                  |\n"
        "|  memory/episodic/*.json                                   |\n"
        "|  - Indexada en ChromaDB (coleccion episodic)              |\n"
        "|  - Ciclo de vida: 24 meses                                |\n"
        "+---------------------------+-------------------------------+\n"
        "|       Consolidacion       |  (confidence >= 0.6)          |\n"
        "+---------------------------+-------------------------------+\n"
        "|  MEMORIA SEMANTICA (conocimiento consolidado)             |\n"
        "|  memory/semantic/*.json                                   |\n"
        "|  - facts, decisions, patterns, mistakes                   |\n"
        "|  - Ciclo de vida: indefinido                              |\n"
        "+---------------------------+-------------------------------+\n"
        "|       Retrieval hibrido   |  (consulta -> ranking)        |\n"
        "+---------------------------+-------------------------------+\n"
        "|  SISTEMA DE RECUPERACION                                  |\n"
        "|  - Scoring: 0.45*vec + 0.2*rec + 0.2*ev + 0.15*conf    |\n"
        "|  - Filtros: proyecto, tags, rango de fechas              |\n"
        "+----------------------------------------------------------+"
    )

    # ---- SECCION 3 ----
    pdf.add_page()
    pdf.titulo("3. Ciclo de Aprendizaje")
    pdf.parrafo(
        "Cada experiencia entrante pasa por un pipeline de 6 etapas que la transforma "
        "de dato crudo a conocimiento consolidado y reusable."
    )
    pdf.subtitulo("Etapa 1: Ingesta")
    pdf.parrafo(
        "Entrada: episodio JSON con campos requeridos (project, source_type, author, "
        "title, summary, timestamp). Se valida el schema, se redacta PII (emails, tokens, "
        "telefonos), se genera embedding_text, se persiste en memory/episodic/ y se indexa "
        "en ChromaDB."
    )
    pdf.subtitulo("Etapa 2: Resumen")
    pdf.parrafo(
        "Se extrae del episodio un resumen estructurado con titulo, decisiones, acciones "
        "y riesgos. Se guarda en memory/summaries/."
    )
    pdf.subtitulo("Etapa 3: Reflexion")
    pdf.parrafo(
        "Opcional. Analiza en batch los episodios de un proyecto para detectar patrones "
        "(tags mas frecuentes) y temas recurrentes. Se guarda en memory/reflections/."
    )
    pdf.subtitulo("Etapa 4: Factcheck")
    pdf.parrafo(
        "Busca en la memoria semantica decisiones similares. Detecta contradicciones "
        "(ej. usar X vs no usar X). Confidence inicial: 0.8 base, -0.3 si hay "
        "contradiccion, -0.2 si no hay evidencia."
    )
    pdf.subtitulo("Etapa 5: Consolidacion")
    pdf.parrafo(
        "Si confidence >= 0.6 y hay >= 1 evidencia, se promueve la decision a memoria "
        "semantica. Si ya existe una decision identica, se incrementa su confidence en "
        "+0.05 y se agrega la nueva fuente de evidencia."
    )
    pdf.subtitulo("Etapa 6: Evaluacion")
    pdf.parrafo(
        "Mide calidad del retrieval: relevance (0-1), has_evidence (bool), "
        "hallucination_risk (0-1). Resultados en logs/evaluations/."
    )
    pdf.ln(2)
    pdf.code_block(
        "                    +-----------------+\n"
        "                    |    INGESTA      |\n"
        "                    +-------+---------+\n"
        "                            |\n"
        "                    Validacion + Redaccion PII + Embedding\n"
        "                            |\n"
        "                    +-------v---------+\n"
        "                    |    RESUMEN      |  -> memory/summaries/\n"
        "                    +-------+---------+\n"
        "                            |\n"
        "                    +-------v---------+\n"
        "                    |   REFLEXION     |  -> memory/reflections/\n"
        "                    +-------+---------+\n"
        "                            |\n"
        "                    +-------v---------+\n"
        "                    |   FACTCHECK     |  -> logs/traces/\n"
        "                    +-------+---------+\n"
        "                            |\n"
        "                    confidence >= 0.6?\n"
        "                            |\n"
        "                    +-------v---------+\n"
        "                    |  CONSOLIDACION  |  -> memory/semantic/\n"
        "                    +-------+---------+  -> ChromaDB index\n"
        "                            |\n"
        "                    +-------v---------+\n"
        "                    |   RETRIEVAL     |  Busqueda hibrida\n"
        "                    +-------+---------+\n"
        "                            |\n"
        "                    +-------v---------+\n"
        "                    |  EVALUACION     |  -> logs/evaluations/\n"
        "                    +-----------------+"
    )

    # ---- SECCION 4 ----
    pdf.add_page()
    pdf.titulo("4. Scoring Hibrido")
    pdf.parrafo(
        "Asigna un peso a cada resultado de retrieval combinando cuatro factores "
        "para determinar la relevancia real de cada item de memoria."
    )
    pdf.sub_subtitulo("Formula")
    pdf.code_block(
        "score = 0.45 * similitud_vectorial\n"
        "      + 0.20 * recencia\n"
        "      + 0.20 * cantidad_evidencia\n"
        "      + 0.15 * confianza_historica"
    )
    pdf.sub_subtitulo("Factores")
    pdf.table(
        ["Factor", "Peso", "Descripcion", "Rango"],
        [
            ["Similitud vectorial", "0.45", "Coseno entre embedding query y doc", "0.0 - 1.0"],
            ["Recencia", "0.20", "Antiguedad del item en dias", "0.2 - 1.0"],
            ["Evidencia", "0.20", "Cantidad de fuentes que respaldan", "0.5 - 1.0"],
            ["Confianza", "0.15", "Score de confianza del item", "0.0 - 1.0"],
        ],
        [45, 18, 100, 27]
    )
    pdf.sub_subtitulo("Recencia (detalle)")
    pdf.table(
        ["Antiguedad", "Score"],
        [["< 7 dias", "1.00"], ["7 - 30 dias", "0.80"], ["30 - 90 dias", "0.60"],
         ["90 - 365 dias", "0.40"], ["> 365 dias", "0.20"]],
        [60, 130]
    )
    pdf.sub_subtitulo("Evidencia (detalle)")
    pdf.parrafo(
        "Formula: 0.5 + 0.5 * (cantidad_evidencia / 5). "
        "Maximo 1.0, minimo 0.0. "
        "Ej: una decision con 3 fuentes: 0.5 + 0.5 * (3/5) = 0.8"
    )

    # ---- SECCION 5 ----
    pdf.add_page()
    pdf.titulo("5. APIs MCP (FastAPI)")
    pdf.parrafo(
        "Servidor MCP via FastAPI para que agentes de IA y herramientas externas "
        "interactuen con la memoria de forma estandarizada."
    )
    pdf.table(
        ["Endpoint", "Metodo", "Proposito"],
        [
            ["/health", "GET", "Health check"],
            ["/ingest", "POST", "Ingestar episodio"],
            ["/retrieve", "POST", "Busqueda hibrida"],
            ["/consolidate", "POST", "Ejecutar consolidacion"],
            ["/evaluate", "POST", "Evaluar calidad retrieval"],
        ],
        [45, 22, 123]
    )
    pdf.note_box(
        "Inicio: uvicorn ai_architect.core.mcp_server:app --reload --port 8000",
        icon="$"
    )
    pdf.sub_subtitulo("Ejemplo retrieve")
    pdf.code_block(
        "POST /retrieve\n"
        '{"query": "autenticacion JWT", "top_k": 3,\n'
        ' "project": "demo-auth", "collection": "semantic"}\n'
        "\n"
        "Respuesta:\n"
        '{"trace_id": "tr_4a9b...",\n'
        ' "results": [{\n'
        '   "id": "sem_bd51...",\n'
        '   "text": "Usar JWT con refresh tokens rotativos",\n'
        '   "score": 0.7497,\n'
        '   "evidence": [{"type": "episode", "id": "ep_45a6..."}]\n'
        " }]}"
    )

    # ---- SECCION 6 ----
    pdf.add_page()
    pdf.titulo("6. Mejoras Futuras Recomendadas")
    pdf.sub_subtitulo("Prioridad Alta")
    pdf.table(
        ["Mejora", "Impacto", "Descripcion"],
        [
            ["Embeddings reales (OpenAI/ST)", "Alto", "Hash actual determinista, pobre semanticamente"],
            ["UI/web dashboard", "Alto", "Visualizar memoria, confianzas y grafos de conocimiento"],
            ["BM25 + embeddings hibridos", "Alto", "Mejor retrieval que solo vectores"],
            ["Pipelines asincronos", "Alto", "Workers para no bloquear el servidor"],
        ],
        [60, 20, 110]
    )
    pdf.sub_subtitulo("Prioridad Media")
    pdf.table(
        ["Mejora", "Impacto", "Descripcion"],
        [
            ["Autenticacion MCP (API key + JWT)", "Medio", "Seguridad en produccion"],
            ["Versionado semantico (supersedes)", "Medio", "Cuando una decision cambia"],
            ["Deteccion de contradicciones con LLM", "Medio", "LLM-based factcheck vs heuristico"],
            ["Export programado (cron/backups)", "Medio", "Backup periodico automatico"],
        ],
        [60, 20, 110]
    )
    pdf.sub_subtitulo("Prioridad Baja")
    pdf.table(
        ["Mejora", "Impacto", "Descripcion"],
        [
            ["Tests de integracion con ChromaDB real", "Bajo", "Tests actuales con hash embedding"],
            ["Dockerfile + docker-compose", "Bajo", "Facil deploy en cualquier entorno"],
            ["MCP stdio server (para OpenCode)", "Bajo", "Alternativa a FastAPI para agentes CLI"],
            ["Agente reflector con LLM", "Bajo", "Reflexiones mas inteligentes que heuristicas"],
        ],
        [60, 20, 110]
    )

    # ---- SECCION 7 ----
    pdf.add_page()
    pdf.titulo("7. Estructura de Datos")
    pdf.subtitulo("7.1 Episodio")
    pdf.parrafo("Cada episodio representa una experiencia o evento unico.")
    pdf.code_block(
        '{\n'
        '  "id": "ep_45a69c4296b04945...",\n'
        '  "project": "demo-auth",\n'
        '  "timestamp": "2026-05-14T18:24:05Z",\n'
        '  "source_type": "meeting",\n'
        '  "author": "ana",\n'
        '  "title": "Decision de autenticacion",\n'
        '  "summary": "Usar JWT con refresh tokens rotativos...",\n'
        '  "decisions": [{"text": "Usar JWT...", "owner": "ana"}],\n'
        '  "risks": [{"text": "Riesgo de claves", "severity": "high"}],\n'
        '  "evidence": [{"type": "doc", "url_or_path": "confluence://...",\n'
        '               "excerpt": "ADR-01 aprueba JWT + refresh rotativo"}],\n'
        '  "tags": ["auth", "seguridad"]\n'
        "}"
    )
    pdf.subtitulo("7.2 Semantico (conocimiento consolidado)")
    pdf.code_block(
        '{\n'
        '  "id": "sem_bd5103e9b5db4642...",\n'
        '  "type": "decision",\n'
        '  "project": "demo-auth",\n'
        '  "statement": "Usar JWT con refresh tokens rotativos",\n'
        '  "confidence": 0.8,\n'
        '  "evidence_source_ids": ["ep_45a6...", "ep_4271..."],\n'
        '  "contradictions": [],\n'
        '  "tags": ["auth", "seguridad"],\n'
        '  "created_at": "2026-05-14T18:24:05Z"\n'
        "}"
    )
    pdf.subtitulo("7.3 Traza de auditoria")
    pdf.parrafo("Toda operacion genera una traza en logs/traces/*.jsonl (JSON Lines).")
    pdf.code_block(
        '{"trace_id": "tr_4a9b...", "ts": "2026-05-14T18:24:05Z",\n'
        ' "operation": "retrieve",\n'
        ' "inputs": {"query": "autenticacion", "top_k": 3},\n'
        ' "outputs": {"count": 1, "results": [...]}}'
    )

    # ---- SECCION 8 ----
    pdf.add_page()
    pdf.titulo("8. Comandos de Uso")
    cmds = [
        ("Demo completa", '$env:PYTHONPATH=".../brain-ai-01"\npython scripts/make_demo.py'),
        ("Servidor MCP", "uvicorn ai_architect.core.mcp_server:app --reload --port 8000"),
        ("Ingestar episodio", "python scripts/ingest_cli.py --file episodio.json"),
        ("Busqueda hibrida", 'python scripts/retrieve_cli.py --query "autenticacion JWT" --project demo-auth'),
        ("Consolidar", "python scripts/consolidate_cli.py --project demo-auth"),
        ("Evaluar", 'python scripts/evaluate_cli.py --query "autenticacion JWT"'),
        ("Tests", "python -m pytest tests/ -v"),
        ("Exportar backup", 'python -c "from ai_architect.pipelines.export import export_all; print(export_all())"'),
    ]
    for title, cmd in cmds:
        pdf.sub_subtitulo(title)
        pdf.code_block(cmd)

    # ---- FINAL ----
    pdf.ln(4)
    pdf.set_draw_color(20, 60, 120)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font("ArialUni", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Fin del manual", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Documento generado automaticamente desde el codigo fuente.", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(OUTPUT))
    print(f"PDF generado: {OUTPUT}")
    print(f"Paginas: {pdf.page_no()}")


if __name__ == "__main__":
    build()
