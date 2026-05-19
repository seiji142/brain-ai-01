"""
Ingestor unificado: detecta formato y llama al script especializado.

Uso:
  python scripts/ingest.py docs/escolaridad.pdf
  python scripts/ingest.py fotos/seiji.jpg --statement "Esta persona es Seiji"
  python scripts/ingest.py notas.md --consolidate
  python scripts/ingest.py https://ejemplo.com --summarize
  python scripts/ingest.py ./carpeta/                    # batch: procesa directorio
"""
import argparse, subprocess, sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
TEXT_EXT = {".md", ".markdown", ".txt", ".rst", ".text", ".env", ".secrets"}
URL_PREFIX = ("http://", "https://")


def _detect_type(input_str: str) -> tuple[str | None, list[str]]:
    """Returns (script_name_or_None, extra_args)"""
    # URL?
    if input_str.startswith(URL_PREFIX):
        return "web_ingest.py", ["--summarize"]

    path = Path(input_str)
    if not path.exists():
        print(f"[ERROR] No encontrado: {input_str}", file=sys.stderr)
        sys.exit(1)

    # Directorio?
    if path.is_dir():
        return "batch_ingest.py", []

    ext = path.suffix.lower()
    if ext in IMAGE_EXT:
        return "img_ingest.py", []
    if ext in TEXT_EXT:
        return "text_ingest.py", []
    if ext == ".pdf":
        return "pdf_ingest.py", []

    # HTML local
    if ext in (".html", ".htm"):
        print(f"[WARN] HTML local: tratando como texto plano")
        return "text_ingest.py", []

    print(f"[ERROR] Extension no soportada: {ext}", file=sys.stderr)
    print(f"  Soportadas: PDF, JPG/PNG/WEBP/GIF/BMP, MD/TXT/RST, URL, directorios", file=sys.stderr)
    sys.exit(1)


def main():
    p = argparse.ArgumentParser(description="Ingestor unificado: cualquier formato a memoria brain-ai-01")
    p.add_argument("input", type=str, help="Archivo, URL o directorio")
    p.add_argument("--project", "-p", default=None, help="Nombre del proyecto")
    p.add_argument("--author", "-a", default=None, help="Autor del episodio")
    p.add_argument("--tags", "-t", default=None, help="Tags separados por coma")
    p.add_argument("--consolidate", "-c", action="store_true", default=None,
                   help="Consolidar al final")
    p.add_argument("--title", "-T", default=None, help="Titulo (texto/imagen/web)")
    p.add_argument("--statement", "-s", default=None, help="Statement/decision (imagen)")
    p.add_argument("--detail", "-d", default=None, choices=["basico", "facial", "full"],
                   help="Nivel de detalle (imagen)")
    p.add_argument("--prompt", "-P", default=None, help="Prompt personalizado (imagen)")
    p.add_argument("--summarize", "-S", action="store_true", default=None, help="Resumir con IA (web)")
    p.add_argument("--selector", "-q", default=None, help="Selector CSS (web)")
    p.add_argument("--pages", "-g", default=None, help="Rango de paginas PDF (ej: 1-5)")
    p.add_argument("--max-chars", "-m", type=int, default=None, help="Max chars por episodio (PDF)")
    p.add_argument("--no-parse", action="store_true", default=None, help="Desactivar parseo (texto)")
    args = p.parse_args()

    script, extra_args = _detect_type(args.input)
    script_path = SCRIPTS_DIR / script

    # Construir cmd base
    cmd = [sys.executable, str(script_path), args.input]

    # Pasar argumentos compartidos que esten definidos
    shared_map = {
        "project": "--project", "author": "--author", "tags": "--tags",
        "consolidate": "--consolidate",
    }
    for attr, flag in shared_map.items():
        val = getattr(args, attr, None)
        if val is not None:
            if isinstance(val, bool) and val:
                cmd.append(flag)
            elif not isinstance(val, bool):
                cmd.extend([flag, str(val)])

    # Pasar argumentos especificos por script
    if script == "img_ingest.py":
        for attr, flag in [("title", "--title"), ("statement", "--statement"),
                           ("detail", "--detail"), ("prompt", "--prompt")]:
            val = getattr(args, attr, None)
            if val is not None:
                cmd.extend([flag, str(val)])
    elif script == "text_ingest.py":
        for attr, flag in [("title", "--title"), ("no-parse", "--no-parse")]:
            val = getattr(args, attr, None)
            if val is not None:
                if isinstance(val, bool) and val:
                    cmd.append(flag)
                elif not isinstance(val, bool):
                    cmd.extend([flag, str(val)])
    elif script == "web_ingest.py":
        for attr, flag in [("title", "--title"), ("summarize", "--summarize"),
                           ("selector", "--selector")]:
            val = getattr(args, attr, None)
            if val is not None:
                if isinstance(val, bool) and val:
                    cmd.append(flag)
                elif not isinstance(val, bool):
                    cmd.extend([flag, str(val)])
    elif script == "pdf_ingest.py":
        for attr, flag in [("pages", "--pages"), ("max-chars", "--max-chars")]:
            val = getattr(args, attr, None)
            if val is not None:
                cmd.extend([flag, str(val)])

    cmd.extend(extra_args)

    print(f"[INGEST] Llamando a {script}...")
    sys.stdout.flush()
    rc = subprocess.call(cmd)
    sys.exit(rc)


if __name__ == "__main__":
    main()
