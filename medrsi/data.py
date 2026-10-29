"""Small data adapters with explicit field and source boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import re

COMPONENTS = ("supporting_findings", "evidence_against",
              "differential_distinctions", "application_instructions")


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_medxpert(row):
    """Convert an upstream Diagnosis row without inferring source identity."""
    if row.get("medical_task") != "Diagnosis":
        raise ValueError("Only Diagnosis rows are supported")
    options = row["options"]
    if (not isinstance(options, dict) or len(options) < 2 or
            not all(isinstance(k, str) and isinstance(v, str) and v.strip()
                    for k, v in options.items()) or row["label"] not in options):
        raise ValueError("Invalid options or reference option")
    if not isinstance(row["question"], str) or not row["question"].strip():
        raise ValueError("Missing question")
    images = row.get("images", [])
    if not isinstance(images, list) or not all(isinstance(x, str) for x in images):
        raise ValueError("Invalid image filenames")
    # Upstream image filenames remain in controller-only metadata.
    image_map = {f"image_{i + 1:03}": name for i, name in enumerate(images)}
    return {
        "id": str(row["id"]),
        "case": {"vignette": row["question"], "image_ids": list(image_map)},
        "candidates": [{"option_id": k, "disease": v} for k, v in options.items()],
        "reference": {"option_id": row["label"]},
        "private_metadata": {"dataset": "MedXpertQA", "image_files": image_map},
    }


def answerer_inputs(record, bank, attached_image_ids=()):
    """Project only public case fields and candidate-specific template fields."""
    case = record["case"]
    images = case.get("image_ids", [])
    attached_image_ids = tuple(attached_image_ids)
    if (len(images) != len(set(images)) or len(attached_image_ids) != len(images)
            or set(images) != set(attached_image_ids)):
        raise ValueError("Every selected image must be attached exactly once")
    candidates = [{"option_id": c["option_id"], "disease": c["disease"]}
                  for c in record["candidates"]]
    if len({c["option_id"] for c in candidates}) != len(candidates):
        raise ValueError("Duplicate option IDs")
    templates = {}
    for candidate in candidates:
        disease = candidate["disease"]
        if disease in bank:
            templates[disease] = {k: deepcopy(bank[disease][k]) for k in COMPONENTS}
    return {"case": {"vignette": case["vignette"], "image_ids": list(images)},
            "candidates": candidates, "current_templates": templates}


def deduplicate_reports(rows):
    """Group transitively by matching nonempty PMCID or DOI, preserving aliases."""
    rows = deepcopy(list(rows))
    parent = list(range(len(rows)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = {}
    for i, row in enumerate(rows):
        pmcid = str(row.get("pmcid") or "").strip().upper()
        doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "",
                     str(row.get("doi") or "").strip(), flags=re.I).lower()
        for key in (("pmcid", pmcid), ("doi", doi)):
            if not key[1]:
                continue
            if key in seen:
                parent[find(i)] = find(seen[key])
            seen[key] = i
    groups = {}
    for i, row in enumerate(rows):
        groups.setdefault(find(i), []).append(row)
    result = []
    for group in groups.values():
        row = group[0]
        row["source_aliases"] = [r["source_id"] for r in group]
        result.append(row)
    return result


def screened_reports(rows, decisions):
    """Keep only groups explicitly cleared by an independent case-overlap screen.

    Decisions must cover every alias. Missing or uncertain reviews stay excluded.
    This consumes review decisions; it does not perform semantic case matching.
    """
    return [r for r in rows if all(decisions.get(s) == "clear"
            for s in r.get("source_aliases", [r["source_id"]]))]


def require_disjoint_sources(partitions):
    """Check supplied source-case groups across practice, validation, and test."""
    seen = {}
    for partition, records in partitions.items():
        for row in records:
            source = row.get("source_case_id")
            if not source:
                raise ValueError("Source-case identity is required")
            if source in seen and seen[source] != partition:
                raise ValueError("Source case occurs in multiple partitions")
            seen[source] = partition
