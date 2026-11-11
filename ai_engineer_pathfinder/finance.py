"""Local revenue and machine-fuel accounting with conservative guardrails.

This module never connects to a bank, moves money, or treats an unverified
entry as revenue. A future payment webhook may append cleared entries after
its signature and payout status are verified.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


DEFAULT_RESERVE_RATIO = Decimal("0.50")


@dataclass(frozen=True)
class FuelSummary:
    cleared_revenue_cents: int
    cleared_cost_cents: int
    reserve_cents: int
    fuel_budget_cents: int
    pending_cents: int
    entry_count: int
    reserve_ratio: str
    transfer_automation: str


def amount_to_cents(value: str | int | float | Decimal) -> int:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid money amount: {value!r}") from exc
    if amount < 0:
        raise ValueError("Money amounts must be non-negative")
    return int(amount * 100)


def money(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _default_ledger() -> dict[str, object]:
    return {
        "currency": "USD",
        "reserve_ratio": str(DEFAULT_RESERVE_RATIO),
        "entries": [],
        "note": "Only verified cleared payouts belong here. This file does not move money.",
    }


def load_ledger(path: Path) -> dict[str, object]:
    if not path.exists():
        return _default_ledger()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _default_ledger()
    if not isinstance(value, dict):
        return _default_ledger()
    value.setdefault("currency", "USD")
    value.setdefault("reserve_ratio", str(DEFAULT_RESERVE_RATIO))
    value.setdefault("entries", [])
    return value


def summarize_ledger(path: Path) -> FuelSummary:
    ledger = load_ledger(path)
    try:
        reserve_ratio = Decimal(str(ledger.get("reserve_ratio", DEFAULT_RESERVE_RATIO)))
    except InvalidOperation:
        reserve_ratio = DEFAULT_RESERVE_RATIO
    reserve_ratio = max(Decimal("0"), min(Decimal("0.90"), reserve_ratio))
    revenue = 0
    costs = 0
    pending = 0
    entries = ledger.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            cents = int(entry.get("amount_cents", 0))
        except (TypeError, ValueError):
            continue
        kind = str(entry.get("kind", ""))
        status = str(entry.get("status", "pending"))
        if status != "cleared":
            pending += cents if kind == "revenue" else -cents if kind == "cost" else 0
        elif kind == "revenue":
            revenue += cents
        elif kind == "cost":
            costs += cents
    net = max(0, revenue - costs)
    reserve = int((Decimal(net) * reserve_ratio).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    fuel = max(0, net - reserve)
    return FuelSummary(
        cleared_revenue_cents=revenue,
        cleared_cost_cents=costs,
        reserve_cents=reserve,
        fuel_budget_cents=fuel,
        pending_cents=pending,
        entry_count=len(entries),
        reserve_ratio=str(reserve_ratio),
        transfer_automation="disabled-until-verified-payment-webhook-and-spending-cap",
    )


def write_fuel_report(output_dir: Path, ledger_path: Path | None = None) -> FuelSummary:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = ledger_path or output_dir / "ledger.json"
    if not ledger_path.exists():
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(_default_ledger(), indent=2) + "\n", encoding="utf-8")
    summary = summarize_ledger(ledger_path)
    payload = asdict(summary)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()
    (output_dir / "latest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Machine fuel report",
        "",
        f"- Cleared revenue: **{money(summary.cleared_revenue_cents)}**",
        f"- Cleared costs: **{money(summary.cleared_cost_cents)}**",
        f"- Reserve ({summary.reserve_ratio}): **{money(summary.reserve_cents)}**",
        f"- Safe fuel budget: **{money(summary.fuel_budget_cents)}**",
        f"- Pending/unverified net: **{money(summary.pending_cents)}**",
        f"- Ledger entries: {summary.entry_count}",
        "",
        "## Policy",
        "",
        "The safe fuel budget is informational. No automatic transfer, purchase, payout withdrawal, or external compute rental is performed.",
        "A future payment integration must verify signed webhooks, cleared payout status, refunds, taxes, and an explicit spending cap before any machine-fueling action is enabled.",
    ]
    (output_dir / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
