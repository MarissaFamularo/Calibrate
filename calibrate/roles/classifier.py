"""Classifier: maps a resident's free-text decision to the case's action IDs for the current
node, or returns "unclear" with an attending-style follow-up. Never guesses. Sequence-dependent
IDs are assigned deterministically after the model call."""
from __future__ import annotations

from ..llm import strict_object

SYSTEM = """You are scoring a surgical resident's spoken/typed plan in a case simulation. Map what they said to ACTION IDs.

Rules:
- Include an action ONLY if the resident explicitly commits to it. Never infer actions from what a good plan would include.
- Negated, declined, or hypothetical items are NOT actions ("I wouldn't get an MRI" -> no MRI action).
- Deferring a problem to the primary care doctor ("PCP can handle", "per PCP", "have his PCP manage") maps to the matching *_per_pcp action.
- "no_..." actions only when the resident explicitly decides against that item.
- List actions in the order the resident says them (order matters for tests and procedures).
- status = "unclear" when the resident's answer does not commit to a specific choice for the core question at this decision point (e.g., "revascularize him" without saying how; "optimize everything"). Then return no actions and write a short, direct attending-style follow-up question asking for the specific missing choice (e.g., "Open or endo? What exactly are you doing?"). Do not hint at the answer.
- status = "clear" otherwise; followup = "".

DECISION POINT: {prompt}

ACTIONS AVAILABLE HERE:
{actions}"""

FOLLOWUPS = {  # engine-requested follow-ups when a clear answer still leaves the node incomplete
    "D3": "Okay. What else before you treat him?",
    "D4": "So what exactly are you doing for him?",
}


def vocabulary(case: dict, node: str) -> list[str]:
    acts = list(case["classifier_actions"].get(node, [])) + list(case["global_actions"])
    return list(dict.fromkeys(acts))


def classify(llm, case: dict, node: str, text: str, dialog: list[tuple[str, str]] | None = None) -> dict:
    """Returns {"status", "actions" (model IDs), "followup"}. `dialog` = prior (speaker, text) at this node."""
    acts = vocabulary(case, node)
    labels = case["action_labels"]
    listing = "\n".join(f"- {a}: {labels[a]}" for a in acts)
    schema = strict_object({
        "status": {"type": "string", "enum": ["clear", "unclear"]},
        "actions": {"type": "array", "items": {"type": "string", "enum": acts}},
        "followup": {"type": "string"},
    })
    convo = "".join(f"{w}: {t}\n" for w, t in (dialog or [])) + f"Resident: {text}"
    out = llm.json("classifier", [
        {"role": "system", "content": SYSTEM.format(prompt=case["nodes"][node]["prompt"], actions=listing)},
        {"role": "user", "content": convo}], schema, "decision_actions")
    out["actions"] = list(dict.fromkeys(a for a in out["actions"] if a in acts))
    if out["status"] == "unclear":
        out["actions"] = []
        out["followup"] = out["followup"].strip() or "Be specific: what exactly are you doing?"
    elif not out["actions"] and node != "D5":
        out.update(status="unclear", followup="What exactly is your plan?")
    return out


def to_engine_actions(node: str, actions: list[str], prior_orders: list[str]) -> list[str]:
    """Assign sequence-dependent engine IDs.
    D3: vein mapping ordered before any angiogram -> vein_mapping_first; angiogram with no prior
        vein mapping -> angio_before_mapping (A3 adopt marker; engine logs the detour).
    D4: any bypass -> bypass_prosthetic (conduit is not the resident's choice; both end in B2)."""
    out, vein_done = [], "vein_mapping" in prior_orders
    for a in actions:
        if node == "D3" and a == "order_vein_mapping":
            angio_done = "angiogram" in prior_orders or any(x in ("order_angiogram", "angio_before_mapping") for x in out)
            out.append("order_vein_mapping" if angio_done else "vein_mapping_first")
            vein_done = True
        elif node == "D3" and a == "order_angiogram":
            out.append("order_angiogram" if vein_done else "angio_before_mapping")
        elif node == "D4" and a == "bypass":
            out.append("bypass_prosthetic")
        else:
            out.append(a)
    return out
