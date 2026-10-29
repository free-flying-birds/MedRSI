"""Strict, JSON-safe rendering of role-specific messages."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    "trace": {"disease", "report"},
    "aggregate": {"disease", "trajectories"},
    "questioner": {"candidates", "target_disease", "evidence"},
    "answerer": {"case", "candidates", "current_templates"},
    "optimizer": {"practice_case", "candidates", "reference_disease",
                  "reference_justification", "reference_evidence",
                  "answerer_response", "current_templates"},
    "updater": {"candidates", "current_templates", "feedback", "evidence"},
}
PLACEHOLDER = re.compile(r"\{\{([a-z_]+)\}\}")


def render(role, bindings):
    if role not in FIELDS or set(bindings) != FIELDS[role]:
        raise ValueError("Unknown role or unexpected/missing input fields")
    text = (ROOT / "prompts" / f"{role}.txt").read_text(encoding="utf-8")
    system, user = text.removeprefix("=== SYSTEM ===\n").split("=== USER ===", 1)
    if set(PLACEHOLDER.findall(user)) != FIELDS[role]:
        raise ValueError("Prompt contract does not match the role")
    payload = PLACEHOLDER.sub(
        lambda m: json.dumps(bindings[m[1]], ensure_ascii=False), user)
    return [{"role": "system", "content": system.strip()},
            {"role": "user", "content": json.dumps(json.loads(payload), ensure_ascii=False)}]
