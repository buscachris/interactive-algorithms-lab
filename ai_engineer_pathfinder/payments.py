"""Signed payment-event ingestion for the local revenue ledger."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .finance import amount_to_cents, load_ledger


class PaymentWebhookError(ValueError):
    """Raised when a payment webhook cannot be safely accepted."""


def verify_lemonsqueezy_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    if not raw_body or not signature or not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())


def _write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def ingest_lemonsqueezy_event(raw_body: bytes, signature: str, secret: str, ledger_path: Path) -> str:
    """Verify and idempotently ingest one Lemon Squeezy order event.

    Only paid USD orders and refunds affect the ledger. The caller must keep
    the endpoint private or place it behind HTTPS and a platform webhook.
    """
    if not verify_lemonsqueezy_signature(raw_body, signature, secret):
        raise PaymentWebhookError("invalid webhook signature")
    try:
        payload = json.loads(raw_body.decode("utf-8"))
        meta = payload["meta"]
        data = payload["data"]
        event_name = str(meta.get("event_name", ""))
        event_id = f"{event_name}:{data['id']}"
        attributes = data["attributes"]
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PaymentWebhookError("invalid webhook JSON shape") from exc

    ledger = load_ledger(ledger_path)
    processed = ledger.setdefault("processed_event_ids", [])
    if not isinstance(processed, list):
        processed = []
        ledger["processed_event_ids"] = processed
    if event_id in processed:
        return "duplicate"

    currency = str(attributes.get("currency", "USD")).upper()
    if currency != "USD":
        processed.append(event_id)
        _write_ledger(ledger_path, ledger)
        return "ignored-non-usd"

    if event_name == "order_created":
        if str(attributes.get("status", "")).casefold() != "paid" or bool(attributes.get("refunded")):
            processed.append(event_id)
            _write_ledger(ledger_path, ledger)
            return "ignored-unpaid-or-refunded"
        kind = "revenue"
        note = "Verified Lemon Squeezy paid order; gross subtotal before fees/taxes."
    elif event_name == "order_refunded":
        kind = "cost"
        note = "Verified Lemon Squeezy refund; reverses the recorded gross subtotal."
    else:
        processed.append(event_id)
        _write_ledger(ledger_path, ledger)
        return "ignored-event"

    raw_amount = attributes.get("subtotal")
    if raw_amount is None:
        raw_amount = attributes.get("subtotal_usd")
        if raw_amount is not None:
            amount_cents = amount_to_cents(raw_amount)
        else:
            raise PaymentWebhookError("paid order has no subtotal")
    else:
        amount_cents = int(raw_amount)
    if amount_cents <= 0:
        raise PaymentWebhookError("paid order has a non-positive subtotal")

    entries = ledger.setdefault("entries", [])
    if not isinstance(entries, list):
        entries = []
        ledger["entries"] = entries
    entries.append(
        {
            "id": event_id,
            "kind": kind,
            "amount_cents": amount_cents,
            "currency": currency,
            "status": "cleared",
            "source": "lemonsqueezy",
            "note": note,
            "occurred_at": attributes.get("created_at") or datetime.now(timezone.utc).isoformat(),
        }
    )
    processed.append(event_id)
    _write_ledger(ledger_path, ledger)
    return "recorded"
