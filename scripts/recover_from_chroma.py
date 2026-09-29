"""Recupera memory/*.json desde Chroma (unica copia tras incidente 29/09/2026).

Por defecto DRY-RUN: no escribe nada, solo genera reporte.
  python scripts/recover_from_chroma.py --report docs/backup_XXX/recovery_report.json
  python scripts/recover_from_chroma.py --write  # escribe JSONs reales faltantes

Perdidas permanentes declaradas en cada objeto (_recovery_lost_fields):
  episodios: author, evidence[], decisions[].owner, limites estructurales
    title/summary/decisions/actions/risks (heuristica por posicion).
  semanticos: evidence_source_ids, contradictions, created_at vs updated_at.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import chromadb

DENY_PROJECTS = {
    "test-project", "eleccion-db", "proyecto-x",
    "proj-alpha", "proj-beta", "proj-gamma", "proj-delta",
    "proj-propio", "proj-otro", "test-batch",
}
ID_PREFIXES = (
    "ep_arq_", "ep_cal_", "ep_test_", "ep_list_", "ep_redact",
    "ep_ingest", "ep_demo", "ep_proj", "ep_batch", "ep_pp",
    "ep_strict", "ep_x",
)


def now_iso() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_fixture(cid: str, project: str) -> bool:
  if (project or "") in DENY_PROJECTS:
    return True
  return cid.startswith(ID_PREFIXES)


def split_doc(doc: str) -> list:
  return [p.strip() for p in (doc or "").split("\n") if p.strip()]


def build_episode(cid: str, meta: dict, doc: str) -> dict:
  parts = split_doc(doc)
  title = parts[0] if parts else cid
  summary = parts[1] if len(parts) > 1 else ""
  # Orden original en ingest.build_embedding_text: title, summary,
  # decisions, actions, risks. Sin estructura: resto -> decisions
  # (maximiza recuperacion en consolidate) + copia cruda para auditoria.
  rest = parts[2:]
  ts = meta.get("timestamp") or now_iso()
  tags = [t for t in (meta.get("tags") or "").split(",") if t]
  return {
      "id": cid,
      "project": meta.get("project", ""),
      "source_type": meta.get("source_type", ""),
      "author": "",
      "title": title,
      "summary": summary,
      "timestamp": ts,
      "created_at": ts,
      "decisions": [{"text": t} for t in rest],
      "actions": [],
      "risks": [],
      "evidence": [],
      "tags": tags,
      "embedding_text": doc,
      "_recovered_from_chroma": True,
      "_recovered_at": now_iso(),
      "_recovery_lost_fields": [
          "author", "evidence[]", "decisions[].owner",
          "actions[]/risks[] (plegados en decisions por heuristica)",
          "limites estructurales title/summary/decisions/actions/risks",
      ],
      "_recovery_notes": (
          "Reconstruido desde Chroma episodic.document "
          "(ingest.build_embedding_text). Linea 1 -> title, "
          "linea 2 -> summary, resto -> decisions[] (heuristica)."
      ),
  }


def build_semantic(cid: str, meta: dict, doc: str) -> dict:
  parts = split_doc(doc)
  # consolidate._build_embedding_text: title, summary, decisions.
  # statement ~= doc sin la primera linea (titulo) si hay >1 linea.
  statement = "\n".join(parts[1:]) if len(parts) > 1 else (parts[0] if parts else "")
  ts = meta.get("timestamp") or now_iso()
  tags = [t for t in (meta.get("tags") or "").split(",") if t]
  return {
      "id": cid,
      "project": meta.get("project", ""),
      "type": meta.get("type", "decision"),
      "title": parts[0] if parts else cid,
      "statement": statement,
      "confidence": float(meta.get("confidence", 0.7) or 0.7),
      "evidence_source_ids": [],
      "contradictions": [],
      "tags": tags,
      "embedding_text": doc,
      "created_at": ts,
      "updated_at": ts,
      "_recovered_from_chroma": True,
      "_recovered_at": now_iso(),
      "_recovery_lost_fields": [
          "evidence_source_ids", "contradictions",
          "created_at vs updated_at (un solo timestamp en Chroma)",
      ],
      "_recovery_notes": (
          "Reconstruido desde Chroma semantic.document "
          "(consolidate._build_embedding_text). statement = doc "
          "menos primera linea (heuristica)."
      ),
  }


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--path", default=".ai_memory/chroma")
  ap.add_argument("--memory", default="memory")
  ap.add_argument("--report", default="")
  ap.add_argument("--write", action="store_true",
                  help="Escribe JSONs (por defecto dry-run).")
  args = ap.parse_args()

  client = chromadb.PersistentClient(path=args.path)
  mem_root = Path(args.memory)
  ep_dir = mem_root / "episodic"
  sem_dir = mem_root / "semantic"

  report = {"episodic": {}, "semantic": {}, "write": args.write}
  for name, builder, target in (
          ("episodic", build_episode, ep_dir),
          ("semantic", build_semantic, sem_dir)):
    col = client.get_or_create_collection(name=name)
    total = col.count()
    got = col.get(limit=total + 10, include=["metadatas", "documents"])
    ids = got.get("ids", [])
    metas = got.get("metadatas", [])
    docs = got.get("documents", [])
    real, fixtures, written, skipped = [], [], [], []
    review = []
    for i, cid in enumerate(ids):
      meta = metas[i] if i < len(metas) else {}
      doc = docs[i] if i < len(docs) else ""
      proj = (meta or {}).get("project", "")
      if is_fixture(cid, proj):
        fixtures.append(cid)
        continue
      real.append(cid)
      if not proj:
        review.append(cid)
      if args.write:
        target.mkdir(parents=True, exist_ok=True)
        dest = target / f"{cid}.json"
        if dest.exists():
          skipped.append(cid)
          continue
        with open(dest, "w", encoding="utf-8") as f:
          json.dump(builder(cid, meta or {}, doc or ""), f,
                    ensure_ascii=False, indent=2)
        written.append(cid)
    report[name] = {
        "total": total,
        "real": len(real),
        "fixtures_skipped": len(fixtures),
        "written": len(written),
        "already_existed": len(skipped),
        "needs_review_empty_project": sorted(review),
    }

  print(json.dumps(report, indent=2))
  if args.report:
    with open(args.report, "w", encoding="utf-8") as f:
      json.dump(report, f, ensure_ascii=False, indent=2)
    print("wrote", args.report)
  if not args.write:
    print("DRY-RUN: nada escrito. Re-ejecutar con --write para materializar.")


if __name__ == "__main__":
  main()
