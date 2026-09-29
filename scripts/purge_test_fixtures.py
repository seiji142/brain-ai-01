"""Purga fixtures de test de Chroma (incidente 29/09/2026, §5 del reporte).

Los tests sin aislamiento indexaron en Chroma real y dejaron items
huerfanos (22 episodic + 305 semantic) que contaminan el ranking.
Solo ejecutar TRAS el backup de .ai_memory/chroma (Fase 1).

  python scripts/purge_test_fixtures.py            # dry-run
  python scripts/purge_test_fixtures.py --write    # borra de verdad
"""
import argparse
import json

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


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--path", default=".ai_memory/chroma")
  ap.add_argument("--write", action="store_true")
  ap.add_argument("--report", default="")
  args = ap.parse_args()

  client = chromadb.PersistentClient(path=args.path)
  report = {"write": args.write}
  for name in ("episodic", "semantic"):
    col = client.get_or_create_collection(name=name)
    total = col.count()
    got = col.get(limit=total + 10, include=["metadatas"])
    ids = got.get("ids", [])
    metas = got.get("metadatas", [])
    targets = [cid for i, cid in enumerate(ids)
               if ((metas[i] or {}).get("project", "") in DENY_PROJECTS
                   or cid.startswith(ID_PREFIXES))]
    report[name] = {"total": total, "purge_targets": len(targets),
                    "sample": sorted(targets)[:8]}
    if args.write and targets:
      col.delete(ids=targets)
      report[name]["after"] = col.count()
  print(json.dumps(report, indent=2))
  if args.report:
    with open(args.report, "w", encoding="utf-8") as f:
      json.dump(report, f, ensure_ascii=False, indent=2)
    print("wrote", args.report)
  if not args.write:
    print("DRY-RUN: nada borrado. Re-ejecutar con --write.")


if __name__ == "__main__":
  main()
