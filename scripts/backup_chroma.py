"""Backup automatico de Chroma (incidente 29/09/2026, Capa 2).

El 29/09/2026 lo unico que salvo la memoria fue `.ai_memory/chroma/`
intacto. Este script hace reversible cualquier futuro accidente:
copia online del sqlite (tolera lock del servidor) + verificacion
reabriendo la copia con `scripts/inventory_chroma.py` y comparando
conteos live vs backup + retencion de las ultimas N copias.

Destino canonico: ver `.ai/checklist_pre_pytest.md`
(`%USERPROFILE%\\brain-ai-01-backups\\chroma`, fuera del arbol git).
Override solo por entorno `BRAIN_BACKUP_ROOT` o flag `--dest-root`.

Nunca toca `memory/` ni el Chroma live en escritura (solo lectura).

Uso:
  python scripts/backup_chroma.py [--dest-root DIR] [--retention 7]
"""
import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LIVE_CHROMA_DIR = REPO_ROOT / ".ai_memory" / "chroma"
LIVE_SQLITE = LIVE_CHROMA_DIR / "chroma.sqlite3"
INVENTORY_SCRIPT = REPO_ROOT / "scripts" / "inventory_chroma.py"

DEFAULT_DEST_ROOT = (
    Path(os.environ["USERPROFILE"]) / "brain-ai-01-backups" / "chroma"
    if os.environ.get("USERPROFILE")
    else REPO_ROOT.parent / "brain-ai-01-backups" / "chroma"
)


def _resolve_dest_root(cli_value: str | None) -> Path:
  raw = cli_value or os.environ.get("BRAIN_BACKUP_ROOT")
  return Path(os.path.expandvars(raw)).resolve() if raw else DEFAULT_DEST_ROOT.resolve()


def _live_counts(chroma_dir: Path) -> dict:
  """Conteos live sin escribir nada (via inventory a tmp)."""
  with tempfile.TemporaryDirectory(prefix="brainai_inv_live_") as tmp:
    out = Path(tmp) / "live_inventory.json"
    subprocess.run(
      [sys.executable, str(INVENTORY_SCRIPT),
       "--path", str(chroma_dir), "--out", str(out)],
      check=True, capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    data = json.loads(out.read_text(encoding="utf-8"))
  return {k: {"total": v["total"], "real": v["real_count"],
              "fixtures": v["fixture_count"]} for k, v in data.items()}


def _backup_counts(sqlite_file: Path) -> dict:
  """Verificacion real: la copia reabre como Chroma y da los mismos conteos."""
  with tempfile.TemporaryDirectory(prefix="brainai_inv_bkp_") as tmp:
    staged = Path(tmp) / "chroma.sqlite3"
    shutil.copyfile(sqlite_file, staged)
    out = Path(tmp) / "backup_inventory.json"
    subprocess.run(
      [sys.executable, str(INVENTORY_SCRIPT),
       "--path", str(Path(tmp)), "--out", str(out)],
      check=True, capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    data = json.loads(out.read_text(encoding="utf-8"))
  return {k: {"total": v["total"], "real": v["real_count"],
              "fixtures": v["fixture_count"]} for k, v in data.items()}


def _prune(dest_root: Path, retention: int) -> list:
  backups = sorted(
    (p for p in dest_root.iterdir()
     if p.is_dir() and p.name.startswith("backup_") and p.name.endswith("_chroma")),
    key=lambda p: p.name,
  )
  removed = []
  for old in backups[:-retention] if len(backups) > retention else []:
    shutil.rmtree(old)
    removed.append(old.name)
  return removed


def main() -> int:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--dest-root", default=None,
                  help="Raiz de backups (default: destino canonico en .ai/checklist_pre_pytest.md)")
  ap.add_argument("--retention", type=int, default=7,
                  help="Cuantas copias conservar (default 7)")
  ap.add_argument("--live-path", default=str(LIVE_CHROMA_DIR),
                  help="Chroma live (solo lectura)")
  ap.add_argument("--allow-inside-repo", action="store_true",
                  help="Permitir destino dentro del repo (solo para pruebas)")
  args = ap.parse_args()

  live_dir = Path(args.live_path)
  live_sqlite = live_dir / "chroma.sqlite3"
  if not live_sqlite.exists():
    print(f"ERROR: no existe {live_sqlite}", file=sys.stderr)
    return 1

  dest_root = _resolve_dest_root(args.dest_root)
  if not args.allow_inside_repo and (
      dest_root == REPO_ROOT or REPO_ROOT in dest_root.parents):
    print(f"ERROR: destino {dest_root} dentro del repo. "
          f"Los backups van fuera del arbol git "
          f"(ver .ai/checklist_pre_pytest.md).", file=sys.stderr)
    return 1

  ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
  dest = dest_root / f"backup_{ts}_chroma"
  dest.mkdir(parents=True, exist_ok=False)
  backup_sqlite = dest / "chroma_online_backup.sqlite3"

  # 1) Copia online consistente (tolera sqlite bloqueado por el servidor).
  src = sqlite3.connect(f"file:{live_sqlite}?mode=ro", uri=True)
  dst = sqlite3.connect(str(backup_sqlite))
  try:
    src.backup(dst)
  finally:
    dst.close()
    src.close()

  # 2) Integridad del archivo copiado.
  con = sqlite3.connect(str(backup_sqlite))
  try:
    integrity = con.execute("PRAGMA integrity_check").fetchall()
  finally:
    con.close()
  if integrity != [("ok",)]:
    print(f"ERROR: integrity_check fallo: {integrity}", file=sys.stderr)
    return 1

  # 3) Verificacion con inventory: la copia reabre y cuenta igual que live.
  live = _live_counts(live_dir)
  backed = _backup_counts(backup_sqlite)
  if live != backed:
    print(f"ERROR: conteos difieren live={live} backup={backed}",
          file=sys.stderr)
    return 1
  subprocess.run(
    [sys.executable, str(INVENTORY_SCRIPT),
     "--path", str(live_dir),
     "--out", str(dest / "chroma_inventory.json")],
    check=True, capture_output=True, text=True, cwd=str(REPO_ROOT),
  )

  meta = {
    "timestamp_local": ts,
    "live_path": str(live_dir),
    "live_sqlite_bytes": live_sqlite.stat().st_size,
    "backup_sqlite_bytes": backup_sqlite.stat().st_size,
    "counts": live,
    "integrity_check": "ok",
    "retention": args.retention,
  }
  (dest / "backup_meta.json").write_text(
    json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

  removed = _prune(dest_root, args.retention)
  remaining = sorted(p.name for p in dest_root.iterdir() if p.is_dir())

  print(json.dumps({"backup": dest.name, "counts": live,
                    "pruned": removed, "remaining": remaining},
                   ensure_ascii=False, indent=2))
  print("OK", dest)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
