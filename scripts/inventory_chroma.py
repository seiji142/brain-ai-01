"""Inventario read-only de Chroma (no escribe en memory/ ni en Chroma).

Uso:
  python scripts/inventory_chroma.py --out docs/backup_XXX/chroma_inventory.json
"""
import argparse
import json
from collections import Counter

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


def is_fixture(cid: str, project: str) -> bool:
  if (project or "") in DENY_PROJECTS:
    return True
  return cid.startswith(ID_PREFIXES)


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--path", default=".ai_memory/chroma")
  ap.add_argument("--out", required=True)
  args = ap.parse_args()

  client = chromadb.PersistentClient(path=args.path)
  out = {}
  for name in ("episodic", "semantic"):
    col = client.get_or_create_collection(name=name)
    total = col.count()
    got = col.get(limit=total + 10, include=["metadatas", "documents"])
    ids = got.get("ids", [])
    metas = got.get("metadatas", [])
    docs = got.get("documents", [])
    by_project = Counter()
    real_ids, fixture_ids = [], []
    for i, cid in enumerate(ids):
      meta = metas[i] if i < len(metas) else {}
      proj = (meta or {}).get("project", "")
      by_project[proj] += 1
      (fixture_ids if is_fixture(cid, proj) else real_ids).append(cid)
    out[name] = {
        "total": total,
        "by_project": dict(sorted(by_project.items())),
        "real_count": len(real_ids),
        "fixture_count": len(fixture_ids),
        "fixture_ids": sorted(fixture_ids),
        "doc_chars_sample": [len(d or "") for d in docs[:5]],
    }
  with open(args.out, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
  print(json.dumps(
      {k: {"total": v["total"], "real": v["real_count"],
            "fixtures": v["fixture_count"]} for k, v in out.items()},
      indent=2))
  print("by_project episodic:", out["episodic"]["by_project"])
  print("by_project semantic:", out["semantic"]["by_project"])
  print("wrote", args.out)


if __name__ == "__main__":
  main()
