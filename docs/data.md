# Data acquisition and preparation

## Public sources

| Resource | Upstream source | Usage |
| --- | --- | --- |
| PMC case reports | [PMC article datasets](https://pmc.ncbi.nlm.nih.gov/tools/pmc-article-datasets/) and [pubget](https://github.com/neuroquery/pubget) | Initialization and evidence retrieval |
| MedXpertQA Text / MM | [Official dataset](https://huggingface.co/datasets/TsinghuaC3I/MedXpertQA) and [code](https://github.com/TsinghuaC3I/MedXpertQA) | Diagnosis task evaluation |
| DiagnosisArena | [Official dataset](https://huggingface.co/datasets/SII-SPIRAL-MED/DiagnosisArena) and [code](https://github.com/SPIRAL-MED/DiagnosisArena) | Differential diagnosis evaluation |
| CuRe-MCQ / CuRe-MCQ-Hard | [Benchmark description](https://arxiv.org/abs/2603.19274) | Multimodal diagnostic evaluation |

The six evaluation settings comprise CuRe-MCQ (500), CuRe-MCQ-Hard (500),
DiagnosisArena-MM (1,113), DiagnosisArena-TXT (1,113), MedXpertQA-MM Diagnosis
(1,199), and MedXpertQA-TXT Diagnosis (1,050).

The linked DiagnosisArena public release contains 915 cases. Record the release
version and case count when preparing an evaluation dataset. Acquire the
corresponding image collection for multimodal evaluation. CuRe release
information is provided in the linked benchmark description.

## Download a few original benchmark records

The downloader streams the first matching Diagnosis rows from an official
MedXpertQA JSONL file, with a hard limit of five. It resolves the requested
revision to a commit SHA and saves the source URL, selection rule, count, and
output checksum alongside the untouched rows.

```bash
python -m scripts.download_examples --subset Text --split test --limit 3
python -m scripts.prepare_data data/raw/medxpert_sample.jsonl data/prepared/text
```

Use `--revision COMMIT_SHA` to repeat a known download. `MM` is also accepted, but
this command does not download `images.zip` or any image files. Acquire images
from the same upstream revision before running multimodal inference. The
[dataset card](https://huggingface.co/datasets/TsinghuaC3I/MedXpertQA/blob/main/README.md)
documents `id`, `question`, `options`, `label`, `images`, and `medical_task`.
The converter selects the Diagnosis task and preserves the question and option
texts. It writes cases and references separately and replaces model-visible
image filenames with neutral handles.

The downloader writes `data/raw/medxpert_sample.provenance.json` alongside its
output. This manifest records the resolved revision, source URL, selection rule,
record count, and output checksum. Dataset attribution and usage terms are
available in the linked upstream dataset card.

## Download and prepare case reports

Select one to five open-access case reports dated 2000–2026 using the
[PMC search interface](https://pmc.ncbi.nlm.nih.gov/). Record numeric PMC IDs,
one per line, in a local `data/pmc_ids.txt`. These must be PMC identifiers,
not PubMed identifiers. Install `pubget` and
record its version in the acquisition manifest:

```bash
python -m pip install pubget
python -m scripts.download_reports --ids data/pmc_ids.txt
python -m scripts.download_reports --ids data/pmc_ids.txt --execute
```

Without `--execute`, the wrapper prints the bounded acquisition command. It
uses pubget's `--pmcids_file` interface. Keep the acquisition metadata, package
version, and source licenses alongside the downloaded articles. Consult
[PMC article datasets](https://pmc.ncbi.nlm.nih.gov/tools/pmc-article-datasets/)
for the supported article access services.

Pass extracted `article.xml` files explicitly:

```bash
python -m scripts.prepare_reports data/pmc/article.xml --output data/reports.jsonl
```

Replace the example XML path with the actual file in pubget's output directory.
The parser retains source IDs, DOI, title, license text, and paragraph locators.
It deduplicates matching PMCIDs/DOIs transitively. Each output is marked pending
case-overlap review. Titles and source metadata belong to the evidence stage;
do not attach them to diagnostic cases.

Next, perform independent source-case comparison against excluded validation
and benchmark cases. Keep that screening outside practice-generation roles and
remove reports describing the same underlying clinical case. The
`screened_reports` helper consumes explicit `clear` / `same_case` decisions;
unreviewed or uncertain records remain excluded. Identifier deduplication alone
cannot detect paraphrased versions of a clinical case.

Only screened reports should enter initialization and practice retrieval.
The retrieval configuration uses `jina-embeddings-v4` with Qdrant. Preserve source
identifiers and paragraph locators when building the retrieval index.

## Separation

Candidate combinations come from independent disease-level construction.
Downloaded benchmark rows are for evaluation and adapter testing; do not use
their candidate sets as the practice construction pool. Validation cases and
labels are reserved for the Judge. Preserve source-case group identities when
partitioning, allocate disjoint validation batches before refinement, and freeze
templates before accessing the final test set.
