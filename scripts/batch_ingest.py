r"""
Orquestador Batch: detecta formato y llama al pre-procesador correcto.

Uso:
  python scripts/batch_ingest.py "C:/Users/seiji/Documentos/"
  python scripts/batch_ingest.py "C:/docs/" --project proyecto-web --tags "batch,importados" --consolidate
  python scripts/batch_ingest.py "C:/fotos/" --only img       # solo imagenes
  python scripts/batch_ingest.py "C:/docs/" --max-files 10    # maximo 10 archivos
"""
import argparse, subprocess, sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

# Extensiones y su script asociado
FORMAT_MAP = {
    # Imagenes
    ".jpg":  ("img_ingest.py",   ["--tags", "batch,imagen"]),
    ".jpeg": ("img_ingest.py",   ["--tags", "batch,imagen"]),
    ".png":  ("img_ingest.py",   ["--tags", "batch,imagen"]),
    ".webp": ("img_ingest.py",   ["--tags", "batch,imagen"]),
    ".gif":  ("img_ingest.py",   ["--tags", "batch,imagen"]),
    ".bmp":  ("img_ingest.py",   ["--tags", "batch,imagen"]),
    # PDF
    ".pdf":  ("pdf_ingest.py",   ["--tags", "batch,pdf"]),
    # Texto / Markdown
    ".md":   ("text_ingest.py",  ["--tags", "batch,markdown"]),
    ".markdown": ("text_ingest.py", ["--tags", "batch,markdown"]),
    ".txt":  ("text_ingest.py",  ["--tags", "batch,texto"]),
    ".rst":  ("text_ingest.py",  ["--tags", "batch,texto"]),
    ".text": ("text_ingest.py",  ["--tags", "batch,texto"]),
}

FORMAT_NAMES = {
    "img":  set([k for k in FORMAT_MAP if k in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")]),
    "pdf":  set([".pdf"]),
    "text": set([".md", ".markdown", ".txt", ".rst", ".text"]),
}


def main():
    p = argparse.ArgumentParser(description="Batch: procesa carpeta entera a memoria")
    p.add_argument("folder", type=str, help="Carpeta a procesar")
    p.add_argument("--project", "-p", default="brain-ai-01", help="Nombre del proyecto")
    p.add_argument("--author", "-a", default="seiji", help="Autor del episodio")
    p.add_argument("--tags", "-t", default="batch", help="Tags extras separados por coma")
    p.add_argument("--only", "-o", default=None, choices=list(FORMAT_NAMES.keys()),
                   help="Solo procesar este tipo (img, pdf, text)")
    p.add_argument("--max-files", "-m", type=int, default=0, help="Max archivos a procesar (0=sin limite)")
    p.add_argument("--consolidate", "-c", action="store_true", help="Consolidar al final")
    p.add_argument("--dry-run", action="store_true", help="Solo mostrar que se procesaria, sin ejecutar")
    args = p.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"[ERROR] Carpeta no encontrada: {folder}", file=sys.stderr)
        sys.exit(1)

    # Recopilar archivos
    files_to_process = []
    only_exts = FORMAT_NAMES.get(args.only, set()) if args.only else set(FORMAT_MAP.keys())

    for f in sorted(folder.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in only_exts and ext in FORMAT_MAP:
            files_to_process.append(f)

    if not files_to_process:
        print(f"[!] No se encontraron archivos procesables en {folder}")
        print(f"    Formatos aceptados: {', '.join(sorted(only_exts))}")
        return

    if args.max_files > 0:
        files_to_process = files_to_process[:args.max_files]

    print(f"=== Batch: {len(files_to_process)} archivo(s) a procesar ===")
    for f in files_to_process:
        rel = f.relative_to(folder) if f.parent == folder else f.relative_to(folder)
        script_name, extra_tags = FORMAT_MAP[f.suffix.lower()]
        print(f"  [{script_name.split('.')[0]}] {rel}")

    if args.dry_run:
        print("\n[Dry-run] No se ejecuto nada. Usa --dry-run para previsualizar.")
        return

    # Ejecutar
    success = 0
    failed = 0
    for file_path in files_to_process:
        script_name, extra_tags = FORMAT_MAP[file_path.suffix.lower()]
        script_path = SCRIPTS_DIR / script_name
        rel = file_path.relative_to(folder) if file_path.parent == folder else file_path.relative_to(folder)

        cmd = [
            sys.executable, str(script_path),
            str(file_path),
            "--project", args.project,
            "--author", args.author,
            "--tags", args.tags + "," + ",".join(extra_tags[-1].split(",")[1:]),
        ]
        # Solo consolidar en el script individual si es el unico archivo
        if len(files_to_process) == 1 and args.consolidate:
            cmd.append("--consolidate")

        print(f"\n>>> [{script_name.split('.')[0]}] {rel}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print(f"  [OK]")
            success += 1
        else:
            print(f"  [ERROR] {result.stderr[:200]}")
            failed += 1

        # Mostrar ultima linea del output
        last_line = [l for l in result.stdout.strip().split("\n") if l.strip()][-1] if result.stdout.strip() else ""
        if last_line and "[OK]" in last_line:
            print(f"  {last_line}")

    # Consolidacion global (si hay mas de 1 archivo)
    if args.consolidate and len(files_to_process) > 1:
        print(f"\n[...] Consolidando proyecto '{args.project}'...")
        import httpx
        try:
            cr = httpx.post("http://localhost:8000/consolidate", json={"project": args.project}, timeout=120)
            if cr.status_code == 200:
                rj = cr.json()
                print(f"[OK] {rj.get('promotions',0)} promociones, {rj.get('contradictions',0)} contradicciones")
        except Exception as e:
            print(f"[WARN] Consolidacion fallo: {e}")

    print(f"\n=== Resumen: {success} OK, {failed} ERRORES, {len(files_to_process)} total ===")


if __name__ == "__main__":
    main()
