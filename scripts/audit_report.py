#!/usr/bin/env python3
"""CLI de reporte de auditoría - analiza logs/audit.jsonl."""

import json
from collections import Counter
from pathlib import Path


def main():
    path = Path("logs/audit.jsonl")
    if not path.exists():
        print("No se encontró logs/audit.jsonl")
        return

    by_type = Counter()
    by_field = Counter()
    by_tool = Counter()
    total_calls = 0

    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("event") != "tool_call":
            continue
        total_calls += 1
        for f in rec.get("findings", []):
            by_type[f["type"]] += 1
            by_field[f.get("field", "?")] += 1
            by_tool[rec.get("tool", "?")] += 1

    print(f"Llamadas totales: {total_calls}\n")
    print("Hallazgos por tipo:")
    for k, v in by_type.most_common():
        print(f"  {k:24} {v}")
    print("\nCampos más problemáticos:")
    for k, v in by_field.most_common(15):
        print(f"  {k:32} {v}")
    print("\nTools más problemáticas:")
    for k, v in by_tool.most_common(10):
        print(f"  {k:24} {v}")


if __name__ == "__main__":
    main()
