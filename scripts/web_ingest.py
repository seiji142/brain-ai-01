"""
Pre-procesador: URL/Web → Episodio en memoria brain-ai-01

Uso:
  python scripts/web_ingest.py https://ejemplo.com
  python scripts/web_ingest.py https://ejemplo.com --project proyecto-web --summarize
  python scripts/web_ingest.py https://ejemplo.com --selector "article.main" --consolidate
"""
import argparse, httpx, json, os, sys, re
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from ai_architect.core.config import PAGES_DIR
from scripts.ingest_utils import mcp_ingest, save_media, build_episode, MCP_URL

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
SUMMARY_MODEL = "meta-llama/llama-3.3-70b-versatile"


def _api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "GROQ_API_KEY"):
        k = os.environ.get(var, "")
        if k:
            return k
    print("[ERROR] OPENROUTER_API_KEY o GROQ_API_KEY no encontrada", file=sys.stderr)
    sys.exit(1)


def _fetch(url: str, selector: str | None) -> tuple[str, str, str, str, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    r = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
    r.raise_for_status()
    html = r.text

    soup = BeautifulSoup(html, "html.parser")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    description = ""
    for meta in soup.find_all("meta"):
        if meta.get("name", "").lower() == "description":
            description = meta.get("content", "")
            break

    if selector:
        selected = soup.select_one(selector)
        if selected:
            soup = selected

    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)

    meta_tags = []
    for kw in soup.find_all("meta"):
        if kw.get("name", "").lower() in ("keywords", "tag", "category"):
            val = kw.get("content", "")
            meta_tags.extend([t.strip() for t in val.split(",") if t.strip()])

    return html, title, text[:50000], description, ",".join(meta_tags[:20])


def _summarize(text: str, url: str) -> str:
    api_key = _api_key()
    payload = {
        "model": SUMMARY_MODEL,
        "messages": [
            {"role": "user", "content": (
                f"Resume el siguiente contenido de la pagina web: {url}\n\n"
                f"Extrae: proposito, puntos clave, y cualquier decision/accion relevante.\n\n"
                f"Contenido:\n{text[:8000]}"
            )}
        ],
        "max_tokens": 1024,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
               "HTTP-Referer": url, "X-Title": "brain-ai-01"}
    r = httpx.post(OPENROUTER_API, json=payload, headers=headers, timeout=60)
    if r.status_code != 200:
        print(f"  [WARN] Error al resumir ({r.status_code}), usando texto plano", file=sys.stderr)
        return text[:2000]
    return r.json()["choices"][0]["message"]["content"]


def _save_page(html: str, url: str, project: str) -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    name = re.sub(r"[^\w]", "_", url.split("//")[-1][:50])
    dest = PAGES_DIR / f"{project}_{ts}_{name}.html"
    dest.write_text(html, encoding="utf-8")
    return dest


def main():
    p = argparse.ArgumentParser(description="Pre-procesador: URL/Web a episodio en memoria")
    p.add_argument("url", type=str, help="URL de la pagina web")
    p.add_argument("--project", "-p", default="brain-ai-01", help="Nombre del proyecto")
    p.add_argument("--selector", "-s", default=None, help="Selector CSS (ej: article.main, #content)")
    p.add_argument("--author", "-a", default="seiji", help="Autor del episodio")
    p.add_argument("--tags", "-t", default="web", help="Tags extras separados por coma")
    p.add_argument("--title", "-T", default=None, help="Titulo (default: title de la pagina)")
    p.add_argument("--summarize", "-S", action="store_true", help="Resumir con IA antes de guardar")
    p.add_argument("--consolidate", "-c", action="store_true", help="Consolidar al final")
    args = p.parse_args()

    url = args.url
    if not url.startswith("http"):
        url = "https://" + url

    # Fetch
    print(f"[...] Descargando {url}...")
    try:
        html, page_title, text, description, meta_tags = _fetch(url, args.selector)
    except Exception as e:
        print(f"[ERROR] No se pudo descargar: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"[OK] Descargado: {len(html)} bytes, {len(text)} chars de texto util")

    # Guardar HTML
    page_path = _save_page(html, url, args.project)
    rel_path = page_path.relative_to(page_path.parent.parent.parent)
    print(f"[OK] HTML guardado: {rel_path}")

    # Resumir opcional
    if args.summarize:
        print("[...] Resumiendo con IA...")
        summary = _summarize(text, url)
        print(f"[OK] Resumen ({len(summary)} chars)")
    else:
        summary = text[:2000]

    # Construir episodio
    ep_title = args.title or page_title or url
    all_tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if meta_tags:
        all_tags.extend([t.strip().lower() for t in meta_tags.split(",") if t.strip()])

    ep = build_episode(
        project=args.project,
        source_type="web",
        author=args.author,
        title=ep_title[:200],
        summary=summary,
        evidence=[{"type": "url", "url_or_path": url, "excerpt": text[:300]}],
        tags=all_tags,
    )

    # Ingestar
    print("[...] Ingestando en memoria...")
    res = mcp_ingest(ep)
    if res:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print("[ERROR] No se pudo ingestar")

    # Consolidar
    if args.consolidate:
        print("[...] Consolidando...")
        cr = httpx.post(f"{MCP_URL}/consolidate", json={"project": args.project}, timeout=60)
        if cr.status_code == 200:
            crj = cr.json()
            print(f"[OK] {crj.get('promotions', 0)} promociones, {crj.get('contradictions', 0)} contradicciones")

    print("[OK] Listo!")


if __name__ == "__main__":
    main()
