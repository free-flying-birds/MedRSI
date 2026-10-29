"""Run pubget on an explicit list of at most five PMC IDs."""
import argparse
from pathlib import Path
import re
import shlex
import subprocess


def command(ids_file, output):
    ids = [x.strip() for x in ids_file.read_text().splitlines() if x.strip()]
    if not 1 <= len(ids) <= 5 or any(not re.fullmatch(r"[0-9]+", x) for x in ids):
        raise ValueError("Provide 1 to 5 numeric PMC IDs, one per line")
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate PMC IDs")
    return ["pubget", "run", str(output), "--pmcids_file", str(ids_file)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/pmc"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    cmd = command(args.ids, args.output)
    if args.execute:
        subprocess.run(cmd, check=True)
    else:
        print(shlex.join(cmd))


if __name__ == "__main__":
    main()
