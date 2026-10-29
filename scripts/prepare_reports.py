"""Extract a bounded set of JATS files into source-linked report records."""
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

from medrsi.data import deduplicate_reports, write_jsonl


def parse_jats(path):
    root = ET.parse(path).getroot()
    article = root if root.tag == "article" else root.find(".//article")
    if article is None:
        raise ValueError("No JATS article element")
    meta = article.find("./front/article-meta")
    if meta is None:
        raise ValueError("No article metadata")
    def text(node):
        return " ".join("".join(node.itertext()).split()) if node is not None else ""
    ids = {x.get("pub-id-type"): text(x) for x in meta.findall("article-id")}
    pmcid = ids.get("pmcid") or ids.get("pmc", "")
    if not pmcid:
        raise ValueError("Missing PMC identifier")
    if not pmcid.startswith("PMC"):
        pmcid = "PMC" + pmcid
    paragraphs = [{"locator": f"body.p{i + 1}", "text": text(p)}
                  for i, p in enumerate(article.findall("./body//p"))]
    return {"source_id": pmcid, "pmcid": pmcid, "doi": ids.get("doi", ""),
            "title": text(meta.find("./title-group/article-title")),
            "license": text(meta.find("./permissions/license")),
            "paragraphs": paragraphs,
            "screen_status": "pending_case_overlap_review"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= len(args.xml) <= 5:
        parser.error("Supply at most five article XML files")
    rows = deduplicate_reports(parse_jats(p) for p in args.xml)
    write_jsonl(args.output, rows)
    print(f"Prepared {len(rows)} reports; case-overlap review remains required.")


if __name__ == "__main__":
    main()
