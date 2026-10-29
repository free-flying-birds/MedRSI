"""One text-only practice/refinement round with injectable model and retrieval calls."""
from copy import deepcopy

from .data import answerer_inputs
from .judge import propose, select_bank


def run_round(bank, candidates, target, evidence, call, judge, batch_id, validation):
    """Call each role once and submit a fixed proposal to the Judge.

    call(role, bindings) must return parsed JSON. Validation prediction uses the
    same Answerer callback. The caller owns batch allocation and source screening.
    """
    names = {c["disease"] for c in candidates}
    if target not in names:
        raise ValueError("Assigned target must belong to the candidate set")
    current = deepcopy(bank)
    practice = call("questioner", {"candidates": deepcopy(candidates),
                    "target_disease": target, "evidence": deepcopy(evidence)})
    if practice.get("eligible") is not True:
        return current, {"accepted": False, "reason": "ineligible_practice"}
    if practice["reference"]["disease"] != target:
        raise ValueError("Questioner changed the assigned target")
    record = {"case": practice["case"], "candidates": candidates}
    inputs = answerer_inputs(record, current)
    response = call("answerer", deepcopy(inputs))
    feedback = call("optimizer", {
        "practice_case": inputs["case"], "candidates": inputs["candidates"],
        "reference_disease": target,
        "reference_justification": practice["reference"]["justification"],
        "reference_evidence": deepcopy(evidence), "answerer_response": response,
        "current_templates": deepcopy(inputs["current_templates"]),
    })
    if feedback.get("practice_validity") != "supported":
        return current, {"accepted": False, "reason": "unsupported_or_ambiguous_practice"}
    update = call("updater", {"candidates": inputs["candidates"],
                  "current_templates": deepcopy(inputs["current_templates"]),
                  "feedback": feedback, "evidence": deepcopy(evidence)})
    selected = update["selected_diseases"]
    revisions = update["revisions"]
    if (len(selected) != len(set(selected)) or
            len(revisions) != len(selected) or
            {r["disease"] for r in revisions} != set(selected)):
        raise ValueError("Revision membership must match selected_diseases exactly")
    known_evidence = {e["evidence_id"] for e in evidence}
    for revision in revisions:
        if not revision.get("change_log"):
            raise ValueError("Every revision requires a change log")
        for change in revision["change_log"]:
            ids = change.get("evidence_ids", [])
            if not ids or not set(ids) <= known_evidence:
                raise ValueError("Revision references unavailable evidence")
    proposed = propose(current, {r["disease"]: r["template"] for r in revisions}, names)
    def predict(case, templates):
        parsed = call("answerer", answerer_inputs(case, templates))
        answer = parsed.get("answer")
        return answer if isinstance(answer, str) else None
    decision = judge.evaluate(current, proposed, batch_id, validation, predict)
    return select_bank(current, proposed, decision), decision
