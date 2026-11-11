"""Local income-pipeline artifacts for a small AI engineering service."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .career import (
    ENTRY_LEVEL_EXCLUSIONS,
    JobLead,
    WWR_BACKEND_FEED,
    WWR_PROGRAMMING_FEED,
    fetch_remotive,
    fetch_wwr,
    filter_and_rank,
    load_leads,
    update_history,
    write_digest,
    write_drafts,
)


def write_income_bundle(output_dir: Path, public_label: str = "Quiet Systems") -> list[Path]:
    """Create client-facing service assets without personal identity data."""
    documents = {
        "README.md": f"""# {public_label} income pipeline

This is a local, CLI-generated package for a fixed-scope private AI workflow
service. It contains no client data, credentials, payment secrets, or personal
identity information.

## Service

The Private AI Workflow Sprint maps one repetitive document or text workflow,
builds a small prototype, adds evaluation checks, and documents limitations and
handoff steps.

## Use

1. Review `offer.md`.
2. Use `intake.md` to qualify a low-risk workflow.
3. Customize `proposal_template.md`.
4. Agree on `scope_of_work.md` before work begins.
5. Use `invoice_template.md` only after a real client and payment terms exist.

The CLI can find public leads and prepare drafts. It does not send proposals,
sign contracts, or claim that a client accepted work.
""",
        "offer.md": f"""# Private AI Workflow Sprint

Provider label: {public_label}

## Promise

One repetitive internal workflow becomes a small, testable AI-assisted
prototype with a clear handoff.

## Deliverables

- workflow map and success definition;
- private/local prototype using approved sample data;
- evaluation set with expected outputs;
- known failure cases and data-handling note;
- setup, test, rollback, and handoff instructions.

## Starter price

Proposed pilot range: **$750–$1,500**, adjusted only after the workflow and
data boundary are clear. This is a quote placeholder, not a promise of market
value or a completed sale.

## Exclusions

No unlimited chatbot, perfect-answer promise, regulated decision-making, or
unapproved access to customer systems.
""",
        "compute_offer.md": f"""# Private Inference and Batch Compute Pilot

Provider label: {public_label}

## Offer

Package one approved AI inference, evaluation, or batch-processing workload
for a private environment with capacity checks, repeatable commands, logs, and
a handoff.

## Deliverables

- workload and input/output boundary;
- local capacity report for CPU, memory, storage, and GPU readiness;
- one repeatable batch or inference runner;
- basic evaluation and failure notes;
- start, stop, cleanup, and handoff instructions.

## Proposed pilot range

**$300–$1,000**, quoted only after the workload, data boundary, and hardware
requirements are reviewed. This is a scope placeholder, not a guaranteed
price or income claim.

## Safety boundary

No arbitrary customer code, secrets, regulated data, or public inbound access
on a personal workstation. External compute hosting requires isolation,
authentication, storage, backup, network, power, and platform-term review.
""",
        "intake.md": """# Client intake

1. What repetitive workflow is slow or error-prone?
2. Who performs it and how often?
3. What inputs and outputs are involved?
4. Can the first pilot use synthetic or redacted examples?
5. What counts as a successful result?
6. What data must never leave the customer's approved environment?
7. Who reviews the output before it is used?
8. What is explicitly out of scope?
""",
        "proposal_template.md": f"""# Proposal — Private AI Workflow Sprint

Provider: {public_label}
Client: [client]
Workflow: [one-sentence workflow]

## Outcome

[Describe the bounded improvement without promising perfect automation.]

## Deliverables

1. Workflow map and success criteria.
2. Small prototype using approved data.
3. Evaluation checks and failure notes.
4. Handoff documentation.

## Schedule and price

Estimated schedule: [dates or number of business days]
Fixed price: $[amount]
Payment terms: [terms]

## Acceptance

Acceptance means the listed deliverables are provided and the documented
happy-path test runs. New workflows or integrations require a new scope.
""",
        "scope_of_work.md": """# Scope of work

## Included

- one workflow;
- one approved data path;
- one prototype implementation;
- one evaluation set;
- one handoff package;
- one revision pass for defects against the agreed acceptance test.

## Not included

- production guarantees;
- legal, medical, financial, or safety decisions;
- handling secrets without an approved secure process;
- unlimited revisions;
- unrelated integrations;
- claims about savings that were not measured.

## Client responsibilities

The client supplies lawful sample data, a decision-maker, access approvals,
acceptance criteria, and timely review.
""",
        "invoice_template.md": """# Invoice template

Invoice number: [number]
Issue date: [date]
Due date: [date]

From: [legal provider name and address]
To: [client legal name and billing address]

## Line item

Private AI Workflow Sprint — [workflow] — $[amount]

Subtotal: $[amount]
Tax: [if applicable]
Total: $[amount]

Payment method: [approved payment method or invoice link]

Do not send this template until the legal provider identity, client, amount,
terms, and payment destination are filled in accurately.
""",
        "delivery_checklist.md": """# Delivery checklist

- [ ] Input and output are documented.
- [ ] Happy-path test passes.
- [ ] At least three failure cases are recorded.
- [ ] Data retention and deletion expectations are written down.
- [ ] No credentials are committed.
- [ ] Setup and rollback steps are present.
- [ ] Client acceptance is recorded.
- [ ] Invoice status is recorded separately from delivery status.
""",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, content in documents.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        paths.append(path)
    return paths


def sync_income_leads(
    output_dir: Path,
    query: str = "AI engineer",
    limit: int = 10,
    leads: Iterable[JobLead] | None = None,
    public_label: str = "Quiet Systems",
) -> tuple[int, list[str]]:
    """Fetch/rank contract-oriented leads and create local proposal drafts."""
    errors: list[str] = []
    if leads is None:
        fetched: list[JobLead] = []
        try:
            fetched.extend(fetch_remotive(query, limit=max(limit, 10)))
        except Exception as exc:  # pragma: no cover - network-dependent
            errors.append(f"Remotive unavailable: {exc}")
        for feed in (WWR_PROGRAMMING_FEED, WWR_BACKEND_FEED):
            try:
                fetched.extend(fetch_wwr(feed))
            except Exception as exc:  # pragma: no cover - network-dependent
                errors.append(f"We Work Remotely unavailable: {exc}")
        leads = fetched

    ranked = filter_and_rank(
        leads,
        query,
        ENTRY_LEVEL_EXCLUSIONS,
        engineering_only=True,
        contract_first=True,
    )
    ranked = [item for item in ranked if item[0] >= 6]
    history = output_dir / "history.json"
    new_ranked = update_history(ranked, history)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "leads.json").write_text(
        json.dumps([lead.to_dict() for _, _, lead in ranked], indent=2) + "\n",
        encoding="utf-8",
    )
    drafts = write_drafts(new_ranked[:limit], output_dir / "proposals", 3, public_label)
    write_digest(new_ranked[:limit], output_dir / "latest.md", drafts)
    return len(new_ranked[:limit]), errors
