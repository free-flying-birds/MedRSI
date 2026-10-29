"""Joint update acceptance using exact rational accuracy differences."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json

from .data import COMPONENTS


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                         separators=(",", ":")).encode()).hexdigest()


def propose(bank, revisions, candidates):
    """Construct a separate bank; never mutate the current collection."""
    if not set(revisions) <= set(candidates):
        raise ValueError("Revision outside the candidate set")
    proposed = deepcopy(bank)
    for disease, template in revisions.items():
        if disease not in bank:
            raise ValueError("Refinement requires an initialized template")
        if any(k not in template or not isinstance(template[k], list) for k in COMPONENTS):
            raise ValueError("All four template components must be lists")
        if template == bank[disease]:
            raise ValueError("An unchanged template is not a revision")
        proposed[disease] = deepcopy(template)
    return proposed


class Judge:
    """Track consumed validation batches and source identities within one process."""
    def __init__(self, delta=0.01, epsilon=0, m_min=5):
        self.delta, self.epsilon = Fraction(str(delta)), Fraction(str(epsilon))
        if self.delta <= 0 or self.epsilon < 0 or type(m_min) is not int or m_min < 1:
            raise ValueError("Invalid acceptance thresholds")
        self.m_min = m_min
        self.used_batches = set()
        self.used_sources = set()

    def evaluate(self, current, proposed, batch_id, cases, predict):
        """predict(case, bank) returns an option ID or None for invalid output.

        The callback must use answerer_inputs and identical decoding settings.
        Transport exceptions abort the decision and consume its reserved batch.
        """
        current, proposed = deepcopy(current), deepcopy(proposed)
        if set(current) != set(proposed):
            raise ValueError("A refinement cannot change the disease vocabulary")
        revised = {d for d in current if current[d] != proposed[d]}
        hashes = {"current_sha256": fingerprint(current),
                  "proposed_sha256": fingerprint(proposed)}
        if not revised:
            return {"accepted": False, "reason": "no_revision", **hashes}
        sources = [c.get("source_case_id") for c in cases]
        ids = [c["id"] for c in cases]
        if (not batch_id or batch_id in self.used_batches or
                any(not s for s in sources) or len(set(sources)) != len(sources) or
                len(set(ids)) != len(ids) or self.used_sources.intersection(sources)):
            raise ValueError("Validation batch is reused or has invalid source identities")
        for c in cases:
            options = {x["option_id"]: x["disease"] for x in c["candidates"]}
            if len(options) != len(c["candidates"]) or c["reference"]["option_id"] not in options:
                raise ValueError("Invalid validation options/reference")
        self.used_batches.add(batch_id)
        self.used_sources.update(sources)
        affected = [c for c in cases if revised.intersection(
                    x["disease"] for x in c["candidates"])]
        groups = {}
        for d in sorted(revised):
            positive, negative = [], []
            for c in affected:
                options = {x["option_id"]: x["disease"] for x in c["candidates"]}
                if d in options.values():
                    target = options[c["reference"]["option_id"]]
                    (positive if target == d else negative).append(c)
            groups[d + ":positive"] = positive
            groups[d + ":negative"] = negative
        report = {**hashes, "batch_id": batch_id, "revised_diseases": sorted(revised),
                  "affected_count": len(affected),
                  "group_counts": {g: len(v) for g, v in groups.items()}}
        if not affected or any(len(v) < self.m_min for v in groups.values()):
            return {**report, "accepted": False, "reason": "insufficient_coverage"}
        changes = {}
        for c in affected:
            # Reference labels and source metadata never enter the predictor.
            public = {k: deepcopy(c[k]) for k in ("id", "case", "candidates")}
            old = predict(deepcopy(public), deepcopy(current))
            new = predict(deepcopy(public), deepcopy(proposed))
            gold = c["reference"]["option_id"]
            changes[c["id"]] = int(new == gold) - int(old == gold)
        def gain(rows):
            return Fraction(sum(changes[c["id"]] for c in rows), len(rows))
        global_gain = gain(affected)
        group_gains = {g: gain(v) for g, v in groups.items()}
        accepted = global_gain > self.delta and all(
            v >= -self.epsilon for v in group_gains.values())
        return {**report, "accepted": accepted,
                "reason": "accepted" if accepted else "accuracy_gate_failed",
                "affected_gain": float(global_gain),
                "group_gains": {g: float(v) for g, v in group_gains.items()}}


def select_bank(current, proposed, decision):
    if (decision["current_sha256"] != fingerprint(current) or
            decision["proposed_sha256"] != fingerprint(proposed)):
        raise ValueError("Template contents changed after validation")
    return deepcopy(proposed if decision["accepted"] else current)
