# Method

## Initialization

Retrieve case reports for each disease, reconstruct source-linked diagnostic
trajectories, and aggregate them into an initial template. Keep explicit negative
findings separate from observations that are unreported. Every template has four
components:

- `supporting_findings`
- `evidence_against`
- `differential_distinctions`
- `application_instructions`

Items may retain their source IDs, scope, and uncertainty. `evidence_gaps` is
optional metadata. Case-report observations do not establish universal exclusion
rules or diagnostic cutoffs.

## Practice and refinement

1. Draw a candidate combination from an independently constructed pool and
   select its target disease uniformly. Construct the pool using general
   disease-level knowledge; exclude benchmark vignettes, images, answers, and
   benchmark-specific candidate combinations.
2. Retrieve supporting material and provide only candidates, target, and evidence
   to the Questioner. It does not receive current templates or past feedback.
3. Provide the new case, candidates, and their current templates to the Answerer.
   Retain the reference diagnosis, reference justification, source packet, and
   generation limitations outside its input.
4. The Optimizer compares the observable answer with the reference and evidence.
   A correct answer may expose a template defect; an incorrect answer does not
   automatically justify a revision.
5. The Updater selects zero or more candidate diseases and returns complete
   revised templates. A competitor's template can be revised. Unselected
   templates remain unchanged.
6. Fix the entire proposal before evaluating a previously allocated validation
   batch. Apply all selected changes jointly or retain the entire previous bank.

`medrsi.workflow.run_round` implements steps 2–6 for text-only inputs. The caller
provides the candidate pool, uniform sampling, retrieved evidence, and a fresh
batch. It also owns the three-round schedule and the shared template collection.

## Validation gate

For revised disease set S, let V_aff contain validation cases whose candidate sets
intersect S. For every disease d in S, build both groups:

- Positive: d is the reference diagnosis.
- Negative: d is a candidate but another option is the reference diagnosis.

Reject if any group has fewer than `m_min = 5` cases. With sufficient coverage,
evaluate current and proposed banks using the same Answerer, case, images,
decoding settings, and budget. Let Delta be proposed accuracy minus current
accuracy, expressed as a fraction. Accept jointly exactly when:

```text
Delta(V_aff) > 0.01
Delta(G) >= 0 for every positive and negative disease group G
```

Equality at the global threshold fails. No failed disease is removed from an
already evaluated proposal to obtain acceptance. Under-covered groups are never
silently skipped. Fifteen single-label cases can provide five positive examples
for at most three revised diseases; all negative groups must also pass coverage.
A single-target batch cannot cover that target's negative group and is rejected.

The Judge reserves each batch before inference, checks source-case reuse, and
binds the decision to hashes of both template banks. Invalid parsed answers
count as incorrect. A transport exception aborts the decision; it is not silently
converted to a diagnostic error. Establish any transport retry policy before
running comparisons. The Judge tracks consumed batches in memory;
durable, transactional state is required across processes and restarts.

## Configuration and evaluation

`configs/default.json` specifies three iterations per combination, 45 validation
cases divided into three disjoint batches of 15, and five independent test
decodings after the final template collection is frozen. Test evaluation never
triggers updates. Calculate accuracy once per complete test run, then summarize
the five run accuracies; do not majority-vote the five answers into a new metric.

The backbone names describe two separate configurations. Within a configuration,
the RSI roles use the same backbone. Endpoint identifiers must be supplied by
the caller. Temperature is 1.0, top-p is 1.0, and the maximum output budget is
16,384 tokens. Top-k truncation and beam search are disabled. Null retrieval
budgets are intentionally unset: choose and record explicit retrieval settings
before a run. No credentials or endpoint assumptions are encoded here.

Validation creation and candidate-pool construction are independent setup steps.
The caller supplies both before refinement and retains their source provenance.

## Data isolation

Top-level field projection prevents reference objects and private metadata from
being forwarded by accident. It cannot detect an answer embedded in a vignette,
a diagnostic image caption, or unsupported clinical guidance within a template.
Source screening and content review remain necessary. Evidence-ID validation
checks that cited records exist; it does not establish that they entail a claim.

`require_disjoint_sources` checks supplied source-case identities across
partitions. Distinct question IDs alone cannot establish patient/source
independence. Keep CuRe variants and corresponding DiagnosisArena text/image
variants grouped when they share an underlying case.
