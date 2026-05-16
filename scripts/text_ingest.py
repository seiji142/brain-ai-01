"""
Pre-procesador: Markdown/TXT → Episodio en memoria brain-ai-01

Uso:
  python scripts/text_ingest.py ruta/notas.md
  python scripts/text_ingest.py ruta/doc.txt --project proyecto-web --consolidate
  python scripts/text_ingest.py ruta/notas.md --section "## Decisiones"
"""
import argparse, httpx, json, shutil, sys, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_architect.core.config import TEXT_DIR

MCP_URL = "http://localhost:8000"


def _parse_env(text: str, title: str) -> dict:
    decisions = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, val = stripped.partition("=")
            key = key.strip()
            val = val.strip()
            if key and val:
                decisions.append({"text": f"Mi {key} es {val}"})
    summary = f"Archivo de secretos: {title}\n" + "\n".join(
        [d["text"] for d in decisions]
    )
    return {
        "title": title,
        "summary": summary,
        "decisions": decisions,
        "actions": [],
        "risks": [],
    }


def _parse_md(text: str, title: str) -> dict:
    lines = text.split("\n")
    decisions = []
    actions = []
    risks = []
    tags = []
    summary_parts = []
    current_section = None

    for line in lines:
        stripped = line.strip()
        # Detectar headings como secciones
        if stripped.startswith("# ") or stripped.startswith("## "):
            section_name = stripped.lstrip("# ").strip().lower()
            current_section = section_name
            summary_parts.append(stripped)

        # Detectar items de lista como decisiones/acciones
        elif stripped.startswith("- ") or stripped.startswith("* "):
            item = stripped[2:].strip()
            if current_section and any(w in current_section for w in ["decision", "acord", "conclus"]):
                decisions.append({"text": item})
            elif current_section and any(w in current_section for w in ["accion", "tarea", "todo", "pendiente"]):
                actions.append({"text": item})
            elif current_section and any(w in current_section for w in ["riesgo", "riesgo", "warning", "cuidado"]):
                risks.append({"text": item})
            summary_parts.append(f"- {item}")

        elif stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            actions.append({"text": stripped[5:].strip(), "done": stripped.startswith("- [x]")})
            summary_parts.append(stripped)

        elif stripped and not stripped.startswith("```"):
            summary_parts.append(stripped)

        # Detectar tags en formato #tag
        found_tags = re.findall(r"#(\w+)", line)
        tags.extend(found_tags)

    summary = "\n".join(summary_parts) if summary_parts else text[:2000]

    return {
        "title": title,
        "summary": summary,
        "decisions": decisions,
        "actions": actions,
        "risks": risks,
    }


def _save_text(src: Path, project: str) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = TEXT_DIR / f"{project}_{ts}_{src.name}"
    shutil.copy2(src, dest)
    return dest


def _mcp_ingest(episode: dict) -> dict:
    r = httpx.post(f"{MCP_URL}/ingest", json={"episode": episode}, timeout=30)
    if r.status_code != 200:
        print(f"  [ERROR] MCP ({r.status_code}): {r.text[:200]}", file=sys.stderr)
        return None
    return r.json()


def main():
    p = argparse.ArgumentParser(description="Pre-procesador: Markdown/TXT a episodio en memoria")
    p.add_argument("file", type=str, help="Ruta al archivo .md o .txt")
    p.add_argument("--project", "-p", default="brain-ai-01", help="Nombre del proyecto")
    p.add_argument("--author", "-a", default="seiji", help="Autor del episodio")
    p.add_argument("--tags", "-t", default="texto,notas", help="Tags extras separados por coma")
    p.add_argument("--title", "-T", default=None, help="Titulo (default: nombre archivo)")
    p.add_argument("--no-parse", action="store_true", help="Desactivar parseo MD, tratar como texto plano")
    p.add_argument("--consolidate", "-c", action="store_true", help="Consolidar al final")
    args = p.parse_args()

    file_path = Path(args.file)

    if not file_path.exists():
        print(f"[ERROR] Archivo no encontrado: {file_path}", file=sys.stderr)
        sys.exit(1)

    ext = file_path.suffix.lower()
    name = file_path.name.lower()
    is_env = name in (".env", ".env.secrets", ".secrets") or ext in (".env", ".secrets")
    if ext not in (".md", ".txt", ".markdown", ".rst", ".text") and not is_env:
        print(f"[ERROR] Formato no soportado: {ext} (usar .md, .txt, .markdown, .env)", file=sys.stderr)
        sys.exit(1)

    # 1) Leer archivo
    text = file_path.read_text(encoding="utf-8")
    print(f"[OK] Archivo: {file_path.name} ({len(text)} chars)")

    # 2) Parsear
    ep_title = args.title or file_path.stem
    source_type = "markdown" if ext in (".md", ".markdown") else "env" if is_env else "text"

    if args.no_parse or ext not in (".md", ".markdown"):
        if is_env:
            parsed = _parse_env(text, ep_title)
        else:
            parsed = {
                "title": ep_title,
                "summary": text[:2000],
                "decisions": [],
                "actions": [],
                "risks": [],
            }
        md_tags = []
    else:
        parsed = _parse_md(text, ep_title)
        md_tags = list(set(re.findall(r"#(\w+)", text)))
        if parsed["decisions"]:
            print(f"  [!] {len(parsed['decisions'])} decision(es) detectadas")
        if parsed["actions"]:
            print(f"  [!] {len(parsed['actions'])} accion(es) detectadas")
        if md_tags:
            print(f"  [!] Tags detectados: {', '.join(md_tags[:10])}")

    if is_env and parsed["decisions"]:
        print(f"  [!] {len(parsed['decisions'])} variable(s) de entorno detectadas")
    print(f"[OK] Parseado: {parsed['title']}")

    # 3) Guardar copia
    text_dest = _save_text(file_path, args.project)
    rel_path = text_dest.relative_to(text_dest.parent.parent.parent)
    print(f"[OK] Copia guardada: {rel_path}")

    # 4) Construir episodio
    all_tags = md_tags + [t.strip() for t in args.tags.split(",") if t.strip()]
    ep = {
        "project": args.project,
        "source_type": source_type,
        "author": args.author,
        "title": parsed["title"],
        "summary": parsed["summary"],
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decisions": parsed["decisions"],
        "actions": parsed["actions"],
        "risks": parsed["risks"],
        "evidence": [{
            "type": source_type,
            "url_or_path": str(rel_path),
            "excerpt": text[:300],
        }],
        "tags": all_tags,
    }

    # 5) Ingestar
    print("[...] Ingestando en memoria...")
    res = _mcp_ingest(ep)
    if res:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("[ERROR] No se pudo ingestar")

    # 6) Consolidar
    if args.consolidate:
        print("[...] Consolidando...")
        cr = httpx.post(f"{MCP_URL}/consolidate", json={"project": args.project}, timeout=60)
        print(f"[OK] Consolidado")
        if cr.status_code == 200:
            crj = cr.json()
            print(f"      {crj.get('promotions', 0)} promociones, {crj.get('contradictions', 0)} contradicciones")

    print("[OK] Listo!")


if __name__ == "__main__":
    main()
