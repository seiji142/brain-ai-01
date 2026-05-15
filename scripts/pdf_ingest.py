"""
Pre-procesador: PDF → Episodio(s) en memoria brain-ai-01

Uso:
  python scripts/pdf_ingest.py ruta/documento.pdf
  python scripts/pdf_ingest.py ruta/doc.pdf --project proyecto-web --consolidate
  python scripts/pdf_ingest.py ruta/doc.pdf --max-chars 5000  # partir en episodios
  python scripts/pdf_ingest.py ruta/doc.pdf --pages 1-5        # solo paginas 1 a 5
"""
import argparse, httpx, json, shutil, sys, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_architect.core.config import PDFS_DIR

MCP_URL = "http://localhost:8000"


def _extract_text(pdf_path: Path) -> tuple[str, int, dict]:
    import fitz
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    meta = doc.metadata or {}
    text_pages = []
    for i, page in enumerate(doc):
        t = page.get_text()
        text_pages.append(t)
    full_text = "\n\n".join(text_pages)
    doc.close()
    return full_text, total_pages, {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "subject": meta.get("subject", ""),
    }


def _chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    while text:
        if len(text) <= max_chars:
            chunks.append(text)
            break
        cut = text.rfind("\n\n", 0, max_chars)
        if cut == -1:
            cut = text.rfind(". ", 0, max_chars)
        if cut == -1:
            cut = max_chars
        chunks.append(text[:cut+1])
        text = text[cut+1:].lstrip()
    return chunks


def _save_pdf(src: Path, project: str) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = PDFS_DIR / f"{project}_{ts}_{src.name}"
    shutil.copy2(src, dest)
    return dest


def _extract_decisions(text: str, title: str, max_decisions: int = 5) -> list[dict]:
    decisions = []
    seen = set()

    def _add(t: str):
        t = t.strip()[:300]
        if t and t.lower() not in seen:
            seen.add(t.lower())
            decisions.append({"text": t})

    if title:
        _add(title)

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for line in lines:
        if len(decisions) >= max_decisions:
            break
        if len(line) < 5:
            continue
        if re.match(r"^(Pagina|pag|Sistema|NOTAS|[-_ ]+)$", line):
            continue
        if re.search(r"\d+%", line):
            _add(line)
        elif re.match(r"^[A-Za-zÁÉÍÓÚáéíóúÑñ][a-záéíóúñ]+.*:", line):
            _add(line)

    if not decisions:
        for line in lines:
            if len(line) >= 20:
                _add(line)
                break

    return decisions


def _mcp_ingest(episode: dict) -> dict:
    r = httpx.post(f"{MCP_URL}/ingest", json={"episode": episode}, timeout=60)
    if r.status_code != 200:
        print(f"  [ERROR] MCP ({r.status_code}): {r.text[:200]}", file=sys.stderr)
        return None
    return r.json()


def _parse_pages(pages_arg: str | None, total: int) -> tuple[int, int]:
    if not pages_arg:
        return 1, total
    try:
        parts = pages_arg.split("-")
        if len(parts) == 1:
            p = int(parts[0])
            return p, p
        return max(1, int(parts[0])), min(total, int(parts[1]))
    except:
        print(f"[ERROR] Formato de --pages invalido: {pages_arg} (ej: 1-10)", file=sys.stderr)
        sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="Pre-procesador: PDF a episodios en memoria")
    p.add_argument("pdf", type=str, help="Ruta al archivo PDF")
    p.add_argument("--project", "-p", default="brain-ai-01", help="Nombre del proyecto")
    p.add_argument("--max-chars", "-m", type=int, default=10000,
                   help="Max caracteres por episodio (0=un solo episodio)")
    p.add_argument("--pages", "-P", default=None, help="Rango de paginas (ej: 1-5, 3)")
    p.add_argument("--author", "-a", default="seiji", help="Autor del episodio")
    p.add_argument("--tags", "-t", default="pdf,documentacion", help="Tags separados por coma")
    p.add_argument("--consolidate", "-c", action="store_true", help="Consolidar al final")
    args = p.parse_args()

    pdf_path = Path(args.pdf)

    # 1) Validar
    if not pdf_path.exists():
        print(f"[ERROR] Archivo no encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print(f"[ERROR] No es un PDF: {pdf_path.suffix}", file=sys.stderr)
        sys.exit(1)

    # 2) Extraer texto
    print(f"[...] Extrayendo texto de {pdf_path.name}...")
    full_text, total_pages, meta = _extract_text(pdf_path)
    pages_start, pages_end = _parse_pages(args.pages, total_pages)
    print(f"[OK] {total_pages} paginas, {len(full_text)} caracteres")

    # 3) Extraer solo las paginas solicitadas
    import fitz
    doc = fitz.open(pdf_path)
    selected = []
    for i in range(pages_start - 1, pages_end):
        selected.append(doc[i].get_text())
    doc.close()
    selected_text = "\n\n".join(selected)

    # 4) Guardar copia del PDF
    pdf_dest = _save_pdf(pdf_path, args.project)
    rel_path = pdf_dest.relative_to(pdf_dest.parent.parent.parent)
    print(f"[OK] PDF guardado: {rel_path}")

    # 5) Partir en chunks si es necesario
    max_chars = args.max_chars or len(selected_text)
    chunks = _chunk_text(selected_text, max_chars)
    print(f"[...] Generando {len(chunks)} episodio(s)...")

    # 6) Ingestar cada chunk
    ep_title_base = meta["title"] or pdf_path.stem
    ingested = []
    for idx, chunk in enumerate(chunks):
        sufijo = f" (parte {idx+1}/{len(chunks)})" if len(chunks) > 1 else ""
        decisions = _extract_decisions(chunk, f"{ep_title_base}{sufijo}")
        ep = {
            "project": args.project,
            "source_type": "pdf",
            "author": args.author,
            "title": f"{ep_title_base}{sufijo}",
            "summary": chunk[:2000],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "decisions": decisions,
            "evidence": [{
                "type": "pdf",
                "url_or_path": str(rel_path),
                "excerpt": chunk[:300]
            }],
            "tags": [t.strip() for t in args.tags.split(",") if t.strip()] + ["pdf"],
        }
        res = _mcp_ingest(ep)
        if res and res.get("ok"):
            ingested.append(res["episode_id"])
            print(f"  [OK] Episodio {idx+1}: {res['episode_id']}")
        else:
            err = res.get("error", "sin respuesta") if res else "sin conexion"
            print(f"  [ERROR] Episodio {idx+1}: {err}")

    # 7) Consolidar
    if args.consolidate and ingested:
        print("[...] Consolidando...")
        cr = httpx.post(f"{MCP_URL}/consolidate", json={"project": args.project}, timeout=120)
        print(f"[OK] Consolidado: {cr.json()}")

    print(f"[OK] Listo! {len(ingested)} episodio(s) creados desde {pdf_path.name}")


if __name__ == "__main__":
    main()
