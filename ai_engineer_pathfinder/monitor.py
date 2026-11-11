"""Local, review-only job monitoring built on the public-feed helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
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


@dataclass(frozen=True)
class MonitorResult:
    """The bounded result of one monitor run."""

    new_leads: int
    total_matches: int
    errors: tuple[str, ...]
    output_dir: Path


def collect_public_leads(
    query: str = "AI engineer",
    source: str = "all",
    limit: int = 50,
) -> tuple[list[JobLead], list[str]]:
    """Read only the selected public feeds and return leads plus warnings."""
    leads: list[JobLead] = []
    errors: list[str] = []
    if source in ("all", "remotive"):
        try:
            leads.extend(fetch_remotive(query, limit=max(limit, 10)))
        except Exception as exc:  # pragma: no cover - network-dependent
            errors.append(f"Remotive unavailable: {exc}")
    if source in ("all", "wwr"):
        for feed in (WWR_PROGRAMMING_FEED, WWR_BACKEND_FEED):
            try:
                leads.extend(fetch_wwr(feed))
            except Exception as exc:  # pragma: no cover - network-dependent
                errors.append(f"We Work Remotely unavailable: {exc}")
    return leads, errors


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _notify(new_ranked: list[tuple[int, list[str], JobLead]], errors: list[str]) -> None:
    """Optionally issue a local desktop notification; never contacts a service."""
    notify_send = shutil.which("notify-send")
    if not notify_send:
        errors.append("notify-send unavailable; digest was still written")
        return
    title = f"Pathfinder: {len(new_ranked)} new job lead(s)"
    body = "\n".join(lead.title for _, _, lead in new_ranked[:3]) or "No new matching leads."
    try:
        subprocess.run([notify_send, title, body], check=False, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover - host-dependent
        errors.append(f"Desktop notification unavailable: {exc}")


def run_monitor(
    output_dir: Path,
    query: str = "AI engineer",
    source: str = "all",
    limit: int = 10,
    leads: Iterable[JobLead] | None = None,
    public_label: str = "Quiet Systems",
    min_score: int = 6,
    notify: bool = False,
) -> MonitorResult:
    """Run one deduplicated monitor pass and write a local review bundle."""
    errors: list[str] = []
    if leads is None:
        fetched, fetch_errors = collect_public_leads(query, source, max(limit, 10))
        leads = fetched
        errors.extend(fetch_errors)

    ranked = filter_and_rank(
        leads,
        query,
        ENTRY_LEVEL_EXCLUSIONS,
        engineering_only=True,
        contract_first=True,
    )
    ranked = [item for item in ranked if item[0] >= min_score]
    history_path = output_dir / "history.json"
    new_ranked = update_history(ranked, history_path)
    visible_new = new_ranked[: max(limit, 0)]

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "leads.json", [lead.to_dict() for _, _, lead in ranked])
    _write_json(output_dir / "new_leads.json", [lead.to_dict() for _, _, lead in visible_new])
    drafts = write_drafts(visible_new, output_dir / "proposals", min(max(limit, 0), 3), public_label)
    write_digest(visible_new, output_dir / "latest.md", drafts)
    now = datetime.now(timezone.utc).isoformat()
    status = {
        "updated_at": now,
        "query": query,
        "source": source,
        "new_leads": len(visible_new),
        "total_matches": len(ranked),
        "errors": errors,
        "digest": str(output_dir / "latest.md"),
    }
    _write_json(output_dir / "status.json", status)
    if notify and visible_new:
        _notify(visible_new, errors)
        status["errors"] = errors
        _write_json(output_dir / "status.json", status)

    return MonitorResult(len(visible_new), len(ranked), tuple(errors), output_dir)


def load_monitor_fixture(path: Path) -> list[JobLead]:
    """Small public helper for deterministic CLI and test runs."""
    return load_leads(path)
