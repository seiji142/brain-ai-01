import zipfile, datetime as dt
from pathlib import Path
from ..core.config import MEMORY_ROOT, LOG_DIR, CHROMA_DIR, ROOT
from ..core.utils import ensure_dir

def export_all(out_dir: str | None = None) -> Path:
    ts = dt.datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%SZ")
    if out_dir is None:
        out_dir = ROOT / ".ai_memory" / "exports"
    ensure_dir(Path(out_dir))
    zip_path = Path(out_dir) / f"{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in [MEMORY_ROOT, LOG_DIR, CHROMA_DIR]:
            if p.exists():
                for f in p.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(ROOT))
    return zip_path
