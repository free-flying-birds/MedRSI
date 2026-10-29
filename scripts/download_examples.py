"""Stream a bounded sample of official MedXpertQA Diagnosis rows."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import urlopen

from medrsi.data import write_jsonl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", choices=["Text", "MM"], default="Text")
    parser.add_argument("--split", choices=["dev", "test"], default="test")
    parser.add_argument("--revision", default="main", help="Commit SHA or branch to resolve")
    parser.add_argument("--limit", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--output", type=Path, default=Path("data/raw/medxpert_sample.jsonl"))
    args = parser.parse_args()
    metadata_path = args.output.with_suffix(".provenance.json")
    if args.output.exists() or metadata_path.exists():
        parser.error("Output already exists; choose a fresh path")
    api = "https://huggingface.co/api/datasets/TsinghuaC3I/MedXpertQA/revision/"
    with urlopen(api + quote(args.revision, safe=""), timeout=60) as handle:
        revision = json.load(handle)["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Upstream did not return a commit SHA")
    url = ("https://huggingface.co/datasets/TsinghuaC3I/MedXpertQA/resolve/"
           f"{revision}/{args.subset}/{args.split}.jsonl")
    rows = []
    with urlopen(url, timeout=60) as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if row.get("medical_task") == "Diagnosis":
                    rows.append(row)
                    if len(rows) == args.limit:
                        break
    if not rows:
        raise ValueError("No Diagnosis records found")
    write_jsonl(args.output, rows)
    provenance = {"source_url": url, "revision": revision,
                  "filter": "medical_task == Diagnosis", "count": len(rows),
                  "selection": "first matching records in upstream order",
                  "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
                  "dataset_card": "https://huggingface.co/datasets/TsinghuaC3I/MedXpertQA",
                  "images_downloaded": False}
    with metadata_path.open("x", encoding="utf-8") as handle:
        json.dump(provenance, handle, indent=2)
    print(f"Saved {len(rows)} records. Image files require separate acquisition.")


if __name__ == "__main__":
    main()
