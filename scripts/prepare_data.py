"""Normalize a small upstream file and separate model inputs from references."""
import argparse
from pathlib import Path

from medrsi.data import normalize_medxpert, read_jsonl, write_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = [normalize_medxpert(r) for r in read_jsonl(args.input)
            if r.get("medical_task") == "Diagnosis"]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate record IDs")
    args.output.mkdir(parents=True, exist_ok=False)
    write_jsonl(args.output / "cases.jsonl", [
        {k: r[k] for k in ("id", "case", "candidates")} for r in rows])
    write_jsonl(args.output / "references.jsonl", [
        {k: r[k] for k in ("id", "reference", "private_metadata")} for r in rows])
    print(f"Prepared {len(rows)} cases and separate reference records.")


if __name__ == "__main__":
    main()
