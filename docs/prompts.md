# Prompt contracts

The Questioner, Answerer, Optimizer, and Updater texts correspond to Appendix C,
Figures 6–9, of *Learning from Diagnostic Practice: Template-Level Recursive
Self-Improvement for Differential Diagnosis*. Wording is preserved with paragraph
wrapping normalized. Trace and Aggregate are companion initialization templates
implementing the trajectory extraction and four-component aggregation procedure.
They are not Appendix C prompt transcriptions.

| Prompt | Inputs |
| --- | --- |
| `trace.txt` | disease, report |
| `aggregate.txt` | disease, trajectories |
| `questioner.txt` | candidates, target_disease, evidence |
| `answerer.txt` | case, candidates, current_templates |
| `optimizer.txt` | practice_case, candidates, reference_disease, reference_justification, reference_evidence, answerer_response, current_templates |
| `updater.txt` | candidates, current_templates, feedback, evidence |

Each file contains `=== SYSTEM ===` and `=== USER ===` sections. The renderer
serializes each `{{placeholder}}` as JSON and requires the exact input-key set.
Placeholder-like text inside a value is not expanded a second time.

```python
from medrsi.data import answerer_inputs
from medrsi.prompts import render

bindings = answerer_inputs(case_record, template_bank)
messages = render("answerer", bindings)
```

Candidates use `{"option_id": "A", "disease": "..."}` records. The Answerer
returns an option ID, preserving the original option labels. Template bank keys
are disease strings. Complete four-component proposals use the `template` key
within each revision object. In the workflow adapter, `practice_validity` is one
of `supported`, `ambiguous`, or `unsupported`; the explanation can be returned in
an additional field. Any unsupported/ambiguous practice record stops refinement.

An image ID is a routing handle, not an image attachment. The data adapter retains
original filenames only in private metadata. A multimodal transport must resolve
each handle, attach the image content, and omit diagnosis-bearing captions and
filenames. The text-only workflow rejects nonempty image lists. The standalone
input projector checks supplied attachment IDs; it cannot inspect transport bytes.

Judge accuracy comparisons are implemented in Python. No model prompt is used
to decide whether the numerical acceptance thresholds pass.
