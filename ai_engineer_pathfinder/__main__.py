"""Command-line interface for Interactive Algorithms Lab."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .arrays import chapter2_demo
from .career import (
    ENTRY_LEVEL_EXCLUSIONS,
    WWR_BACKEND_FEED,
    WWR_PROGRAMMING_FEED,
    JobLead,
    draft_application,
    fetch_remotive,
    fetch_wwr,
    filter_and_rank,
    load_leads,
    update_history,
)
from .planner import Pathfinder, default_data_path
from .sorting import chapter3_demo
from .stacks_queues import chapter4_demo
from .linked_lists import chapter5_demo
from .income import sync_income_leads, write_income_bundle
from .monitor import load_monitor_fixture, run_monitor
from .compute import write_compute_report
from .finance import money, write_fuel_report
from .product import PRODUCT_VERSION, build_release


DEFAULT_COMPLETED = {"python", "git"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Explore Interactive Algorithms Lab examples and workflows.")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("dashboard", help="show progress and recommended next skills")
    subparsers.add_parser("chapter2", help="demonstrate arrays and binary search")
    subparsers.add_parser("chapter3", help="demonstrate simple sorting algorithms")
    subparsers.add_parser("chapter4", help="demonstrate stacks, queues, and parsing")
    subparsers.add_parser("chapter5", help="demonstrate linked lists and iterators")

    compute = subparsers.add_parser("compute", help="report local AI compute capacity and blockers")
    compute.add_argument("--output", type=Path, default=Path("compute_output"))

    finance = subparsers.add_parser("finance", help="report verified revenue and the conservative machine-fuel budget")
    finance.add_argument("--output", type=Path, default=Path("finance_output"))
    finance.add_argument("--ledger", type=Path, help="ledger JSON path; defaults inside the output directory")

    search = subparsers.add_parser("search", help="search skill records")
    search.add_argument("query")

    next_command = subparsers.add_parser("next", help="rank eligible next skills")
    next_command.add_argument("--completed", nargs="*", default=sorted(DEFAULT_COMPLETED))
    next_command.add_argument("--limit", type=int, default=5)

    path = subparsers.add_parser("path", help="find a prerequisite-forward path")
    path.add_argument("target", nargs="?", default="portfolio")
    path.add_argument("--completed", nargs="*", default=sorted(DEFAULT_COMPLETED))

    career = subparsers.add_parser("career", help="discover and draft AI-engineering opportunities")
    career_commands = career.add_subparsers(dest="career_command")

    career_search = career_commands.add_parser("search", help="rank public remote job-feed listings")
    career_search.add_argument("--query", default="AI engineer")
    career_search.add_argument("--source", choices=("all", "remotive", "wwr"), default="all")
    career_search.add_argument("--limit", type=int, default=10)
    career_search.add_argument(
        "--entry-level",
        action="store_true",
        help="exclude senior, staff, principal, lead, director, and manager titles",
    )
    career_search.add_argument(
        "--engineering-only",
        action="store_true",
        help="keep engineering, developer, architect, and infrastructure titles",
    )
    career_search.add_argument(
        "--contract-first",
        action="store_true",
        help="prefer contract/freelance work and skip explicit screening barriers",
    )
    career_search.add_argument("--offline", type=Path, help="read leads from a local JSON fixture instead")
    career_search.add_argument("--save", type=Path, help="save ranked leads locally as JSON")
    career_search.add_argument("--draft-dir", type=Path, help="write local drafts for the top matches")
    career_search.add_argument("--draft-limit", type=int, default=3)
    career_search.add_argument("--label", default="Quiet Systems")
    career_search.add_argument("--min-score", type=int, default=0)
    career_search.add_argument("--history", type=Path, help="remember listing URLs between runs")
    career_search.add_argument("--new-only", action="store_true", help="show and draft only unseen listings")
    career_search.add_argument("--digest", type=Path, help="write a compact local review queue")

    career_draft = career_commands.add_parser("draft", help="print a truthful application draft for one lead")
    career_draft.add_argument("--title", required=True)
    career_draft.add_argument("--company", default="")
    career_draft.add_argument("--url", default="")
    career_draft.add_argument("--label", default="Quiet Systems")

    career_monitor = career_commands.add_parser(
        "monitor",
        help="run one local, review-only pass over public job feeds",
    )
    career_monitor.add_argument("--query", default="AI engineer")
    career_monitor.add_argument("--source", choices=("all", "remotive", "wwr"), default="all")
    career_monitor.add_argument("--limit", type=int, default=10)
    career_monitor.add_argument("--min-score", type=int, default=6)
    career_monitor.add_argument("--output", type=Path, default=Path("career_output"))
    career_monitor.add_argument("--label", default="Quiet Systems")
    career_monitor.add_argument("--offline", type=Path, help="read a local JSON fixture instead")
    career_monitor.add_argument("--notify", action="store_true", help="try a local notify-send alert")

    income = subparsers.add_parser("income", help="build an AI service income pipeline")
    income.add_argument("--output", type=Path, default=Path("income_output"))
    income.add_argument("--label", default="Quiet Systems")
    income.add_argument("--sync-leads", action="store_true", help="also fetch public contract-oriented leads")
    income.add_argument("--offline", type=Path, help="use a local JSON lead fixture instead of fetching")

    product = subparsers.add_parser("product", help="build the sanitized toolkit release")
    product_commands = product.add_subparsers(dest="product_command")
    product_build = product_commands.add_parser("build", help="create a distributable zip archive")
    product_build.add_argument("--output", type=Path, default=Path("product_output/interactive-algorithms-lab-v0.1.0.zip"))
    product_build.add_argument("--version", default=PRODUCT_VERSION)
    return parser


def _load() -> Pathfinder:
    return Pathfinder.from_json(default_data_path())


def _print_skill(skill, prefix: str = "-") -> None:
    print(f"{prefix} {skill.id}: {skill.title} [{skill.category}] (priority {skill.importance})")
    print(f"  {skill.description}")


def _print_lead(rank: int, score: int, matched: list[str], lead: JobLead) -> None:
    location = f" | {lead.location}" if lead.location else ""
    company = f" — {lead.company}" if lead.company else ""
    print(f"{rank}. [{score}] {lead.title}{company}{location}")
    print(f"   {lead.source} | {lead.url}")
    if lead.salary:
        print(f"   Salary: {lead.salary}")
    if matched:
        print(f"   Matched: {', '.join(matched)}")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    pathfinder = _load()
    command = args.command or "dashboard"

    if command == "dashboard":
        finished, total, percentage = pathfinder.progress(DEFAULT_COMPLETED)
        print("Interactive Algorithms Lab")
        print("===========================")
        print(f"Progress baseline: {finished}/{total} skills ({percentage:.0f}%)")
        print("Completed keys:", ", ".join(sorted(DEFAULT_COMPLETED)))
        print("\nRecommended next skills:")
        for skill in pathfinder.next_skills(DEFAULT_COMPLETED):
            _print_skill(skill)
        return 0

    if command == "chapter2":
        print(chapter2_demo())
        return 0

    if command == "chapter3":
        print(chapter3_demo())
        return 0

    if command == "chapter4":
        print(chapter4_demo())
        return 0

    if command == "chapter5":
        print(chapter5_demo())
        return 0

    if command == "compute":
        report = write_compute_report(args.output)
        print(f"Private batch/inference: {'READY' if report.private_batch_ready else 'CAUTION'}")
        print(f"External GPU hosting: {'READY' if report.external_gpu_hosting_ready else 'BLOCKED'}")
        print(f"CPU threads: {report.cpu_threads}")
        print(f"Memory available: {report.memory_available_gib} GiB")
        print(f"Disk free: {report.disk_free_gib} GiB")
        print(f"GPU: {report.gpu_name} ({report.gpu_memory})")
        print(f"Report: {args.output / 'latest.md'}")
        for blocker in report.blockers:
            print(f"Blocker: {blocker}")
        return 0

    if command == "finance":
        summary = write_fuel_report(args.output, args.ledger)
        print(f"Cleared revenue: {money(summary.cleared_revenue_cents)}")
        print(f"Cleared costs: {money(summary.cleared_cost_cents)}")
        print(f"Reserve: {money(summary.reserve_cents)}")
        print(f"Safe fuel budget: {money(summary.fuel_budget_cents)}")
        print(f"Pending/unverified net: {money(summary.pending_cents)}")
        print(f"Report: {args.output / 'latest.md'}")
        print("Automatic transfers: disabled until verified payment webhook and spending cap")
        return 0

    if command == "search":
        results = pathfinder.catalog.search(args.query)
        print(f"Search results for {args.query!r}: {len(results)}")
        for skill in results:
            _print_skill(skill)
        return 0

    if command == "next":
        print("Eligible next skills:")
        for skill in pathfinder.next_skills(args.completed, args.limit):
            _print_skill(skill)
        return 0

    if command == "path":
        skills = pathfinder.path_to(args.target, args.completed)
        if not skills:
            print(f"No path found from {args.completed} to {args.target}.")
            return 1
        print(f"Learning path to {args.target}:")
        print(" -> ".join(skill.title for skill in skills))
        print("Keys:", " -> ".join(skill.id for skill in skills))
        return 0

    if command == "career":
        if args.career_command == "draft":
            lead = JobLead(source="manual", title=args.title, company=args.company, url=args.url)
            print(draft_application(lead, args.label))
            return 0

        if args.career_command == "monitor":
            leads = load_monitor_fixture(args.offline) if args.offline else None
            result = run_monitor(
                args.output,
                query=args.query,
                source=args.source,
                limit=args.limit,
                leads=leads,
                public_label=args.label,
                min_score=args.min_score,
                notify=args.notify,
            )
            print(f"New leads: {result.new_leads}")
            print(f"Current matches: {result.total_matches}")
            print(f"Digest: {result.output_dir / 'latest.md'}")
            for error in result.errors:
                print(f"Warning: {error}")
            return 0

        if args.career_command == "search":
            if args.offline:
                leads = load_leads(args.offline)
            else:
                leads = []
                errors: list[str] = []
                if args.source in ("all", "remotive"):
                    try:
                        leads.extend(fetch_remotive(args.query, limit=max(args.limit, 10)))
                    except Exception as exc:  # pragma: no cover - depends on network/feed state
                        errors.append(f"Remotive unavailable: {exc}")
                if args.source in ("all", "wwr"):
                    for feed in (WWR_PROGRAMMING_FEED, WWR_BACKEND_FEED):
                        try:
                            leads.extend(fetch_wwr(feed))
                        except Exception as exc:  # pragma: no cover - depends on network/feed state
                            errors.append(f"We Work Remotely unavailable: {exc}")
                if errors:
                    for error in errors:
                        print(f"Warning: {error}")

            excluded = ENTRY_LEVEL_EXCLUSIONS if args.entry_level else ()
            ranked = filter_and_rank(leads, args.query, excluded, args.engineering_only, args.contract_first)
            ranked = [item for item in ranked if item[0] >= args.min_score]
            new_ranked = update_history(ranked, args.history) if args.history else ranked
            visible = new_ranked if args.new_only else ranked
            visible = visible[: max(args.limit, 0)]
            if args.new_only:
                print(f"New career leads for {args.query!r}: {len(visible)} (current matches: {len(ranked)})")
            else:
                print(f"Career leads for {args.query!r}: {len(visible)}")
            for rank, (score, matched, lead) in enumerate(visible, start=1):
                _print_lead(rank, score, matched, lead)
            if args.save:
                args.save.parent.mkdir(parents=True, exist_ok=True)
                args.save.write_text(
                    json.dumps([lead.to_dict() for _, _, lead in ranked], indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"Saved: {args.save}")
            if args.draft_dir:
                from .career import write_drafts

                written = write_drafts(visible, args.draft_dir, args.draft_limit, args.label)
                for path in written:
                    print(f"Draft: {path}")
            else:
                written = []
            if args.digest:
                from .career import write_digest

                write_digest(visible, args.digest, written)
                print(f"Digest: {args.digest}")
            if args.history:
                print(f"History: {args.history}")
            return 0

        print("Use `career search` or `career draft`.")
        return 2

    if command == "income":
        paths = write_income_bundle(args.output, args.label)
        print(f"Income bundle: {args.output}")
        print(f"Client assets: {len(paths)}")
        if args.sync_leads or args.offline:
            leads = load_leads(args.offline) if args.offline else None
            new_count, errors = sync_income_leads(args.output, leads=leads, public_label=args.label)
            for error in errors:
                print(f"Warning: {error}")
            print(f"New contract-oriented leads: {new_count}")
            print(f"Review queue: {args.output / 'latest.md'}")
            print(f"Proposal drafts: {args.output / 'proposals'}")
        return 0

    if command == "product":
        if args.product_command not in (None, "build"):
            print("Use `product build`.")
            return 2
        output_zip, manifest_path, files = build_release(args.output, args.version)
        print(f"Product archive: {output_zip}")
        print(f"Manifest: {manifest_path}")
        print(f"Packaged files: {len(files)}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
