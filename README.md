# MedRSI

Template-level recursive self-improvement for differential diagnosis.

MedRSI organizes source-grounded diagnostic guidance into disease-specific
templates. A Questioner constructs a new exercise, an Answerer applies the
current templates, an Optimizer identifies supported guidance problems, and an
Updater proposes selective revisions. A separate Judge evaluates the complete
proposal before updating the shared template collection.

This repository contains template-refinement utilities, role prompts,
configuration, and scripts for acquiring and preparing public medical datasets.

## Quick start

Python 3.10 or later is required. The data-processing utilities use the Python
standard library. Run commands from this directory.

```bash
python -m scripts.download_examples --subset Text --split test --limit 3
python -m scripts.prepare_data data/raw/medxpert_sample.jsonl data/prepared/text
```

The downloader saves a small sample from the official MedXpertQA release and
records its source revision and checksum. The preparation script preserves
questions and options, then writes separate `cases.jsonl` and `references.jsonl`
files. The reference labels remain outside Answerer inputs.

Output paths must be new. Generated files live under ignored directories.

## Contents

| Path | Contents |
| --- | --- |
| `medrsi/` | Data boundaries, prompt rendering, proposal construction, and Judge |
| `prompts/` | Questioner, Answerer, Optimizer, Updater, Trace, and Aggregate |
| `configs/default.json` | Decoding settings, iteration schedule, and gate thresholds |
| `scripts/` | Small public-data downloads and data preparation |
| `docs/` | Method, data acquisition, and prompt contracts |

See [data acquisition](docs/data.md), [method details](docs/method.md),
and [prompt contracts](docs/prompts.md).

## Model integration

`medrsi.workflow.run_round` executes a text-only refinement round through
`call(role, bindings)`. Supply a model callback returning parsed JSON, screened
retrieval evidence, initialized templates, and a fresh validation batch. The
Judge applies the global-improvement, disease-group, and coverage conditions
before selecting the next template bank.

The data acquisition guide links to the upstream datasets and their usage terms.
