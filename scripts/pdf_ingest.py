"""
Pre-procesador: PDF → Episodio(s) en memoria brain-ai-01

Uso:
  python scripts/pdf_ingest.py ruta/documento.pdf
  python scripts/pdf_ingest.py ruta/doc.pdf --project proyecto-web --consolidate
  python scripts/pdf_ingest.py ruta/doc.pdf --max-chars 5000
  python scripts/pdf_ingest.py ruta/doc.pdf --pages 1-5
"""
import argparse, httpx, sys, re
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_architect.core.config import PDFS_DIR
from scripts.ingest_utils import mcp_ingest, save_media, extract_decisions, build_episode, MCP_URL


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

    if not pdf_path.exists():
        print(f"[ERROR] Archivo no encontrado: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    if pdf_path.suffix.lower() != ".pdf":
        print(f"[ERROR] No es un PDF: {pdf_path.suffix}", file=sys.stderr)
        sys.exit(1)

    # Extraer texto
    print(f"[...] Extrayendo texto de {pdf_path.name}...")
    full_text, total_pages, meta = _extract_text(pdf_path)
    pages_start, pages_end = _parse_pages(args.pages, total_pages)
    print(f"[OK] {total_pages} paginas, {len(full_text)} caracteres")

    # Paginas solicitadas
    import fitz
    doc = fitz.open(pdf_path)
    selected = []
    for i in range(pages_start - 1, pages_end):
        selected.append(doc[i].get_text())
    doc.close()
    selected_text = "\n\n".join(selected)

    # Guardar copia del PDF
    pdf_dest = save_media(pdf_path, args.project, PDFS_DIR)
    rel_path = pdf_dest.relative_to(pdf_dest.parent.parent.parent)
    print(f"[OK] PDF guardado: {rel_path}")

    # Partir en chunks
    max_chars = args.max_chars or len(selected_text)
    chunks = _chunk_text(selected_text, max_chars)
    print(f"[...] Generando {len(chunks)} episodio(s)...")

    # Ingestar cada chunk
    ep_title_base = meta["title"] or pdf_path.stem
    ingested = []
    for idx, chunk in enumerate(chunks):
        sufijo = f" (parte {idx+1}/{len(chunks)})" if len(chunks) > 1 else ""
        decisions = extract_decisions(chunk, f"{ep_title_base}{sufijo}")
        ep = build_episode(
            project=args.project,
            source_type="pdf",
            author=args.author,
            title=f"{ep_title_base}{sufijo}",
            summary=chunk[:2000],
            decisions=decisions,
            evidence=[{"type": "pdf", "url_or_path": str(rel_path), "excerpt": chunk[:300]}],
            tags=[t.strip() for t in args.tags.split(",") if t.strip()] + ["pdf"],
        )
        res = mcp_ingest(ep)
        if res and res.get("ok"):
            ingested.append(res["episode_id"])
            print(f"  [OK] Episodio {idx+1}: {res['episode_id']}")
        else:
            err = res.get("error", "sin respuesta") if res else "sin conexion"
            print(f"  [ERROR] Episodio {idx+1}: {err}")

    # Consolidar
    if args.consolidate and ingested:
        print("[...] Consolidando...")
        cr = httpx.post(f"{MCP_URL}/consolidate", json={"project": args.project}, timeout=120)
        print(f"[OK] Consolidado: {cr.json()}")

    print(f"[OK] Listo! {len(ingested)} episodio(s) creados desde {pdf_path.name}")


if __name__ == "__main__":
    main()
