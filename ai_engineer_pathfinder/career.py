"""Privacy-conscious job discovery and application-draft helpers.

The module only reads public feeds/APIs and produces local output. It never
logs in, submits applications, sends messages, or stores credentials.
"""

from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


REMOTIVE_API = "https://remotive.com/api/remote-jobs"
WWR_PROGRAMMING_FEED = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
WWR_BACKEND_FEED = "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss"
DEFAULT_KEYWORDS = (
    "python",
    "ai",
    "llm",
    "machine learning",
    "rag",
    "agent",
    "automation",
    "evaluation",
    "backend",
    "api",
    "docker",
    "fastapi",
)
LOWER_PRIORITY_TERMS = ("senior", "staff", "principal", "director", "manager")
ENTRY_LEVEL_EXCLUSIONS = LOWER_PRIORITY_TERMS + ("lead",)
ENGINEERING_TITLE_TERMS = (
    "engineer",
    "engineering",
    "developer",
    "architect",
    "backend",
    "software",
    "infrastructure",
    "machine learning",
    "ml ",
    "data scientist",
)
NON_ENGINEERING_TITLE_TERMS = (
    "marketing",
    "sales",
    "support",
    "customer success",
    "recruit",
    "designer",
    "account executive",
    "legal",
    "finance",
)
CONTRACT_TERMS = (
    "contract",
    "contractor",
    "freelance",
    "consultant",
    "consulting",
    "independent",
    "part-time",
    "project-based",
    "subcontract",
)
SCREENING_TERMS = (
    "background check",
    "criminal background",
    "security clearance",
    "clearance required",
    "public trust",
    "citizenship required",
    "government contract",
)


class _TextExtractor(HTMLParser):
    """Convert feed descriptions to compact plain text."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", html.unescape(" ".join(self.parts))).strip()


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    return parser.text()


@dataclass(frozen=True)
class JobLead:
    """A public job listing normalized across feed formats."""

    source: str
    title: str
    company: str
    url: str
    location: str = ""
    published: str = ""
    description: str = ""
    job_type: str = ""
    salary: str = ""

    @classmethod
    def from_dict(cls, record: dict[str, Any]) -> "JobLead":
        return cls(
            source=str(record.get("source", "local")),
            title=str(record.get("title", "Untitled role")),
            company=str(record.get("company", record.get("company_name", "Unknown company"))),
            url=str(record.get("url", "")),
            location=str(record.get("location", record.get("candidate_required_location", ""))),
            published=str(record.get("published", record.get("publication_date", ""))),
            description=_plain_text(str(record.get("description", ""))),
            job_type=str(record.get("job_type", "")),
            salary=str(record.get("salary", "")),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def score(self, keywords: Iterable[str] = DEFAULT_KEYWORDS) -> tuple[int, list[str]]:
        """Score a lead for the user's applied-AI target without pretending it is a fit."""
        title = self.title.lower()
        haystack = f"{self.title} {self.description} {self.job_type}".lower()
        matched: list[str] = []
        score = 0
        for keyword in keywords:
            if keyword.lower() in haystack:
                matched.append(keyword)
                score += 3 if keyword.lower() in title else 1
        if any(term in title for term in LOWER_PRIORITY_TERMS):
            score -= 2
        if "remote" in f"{self.location} {self.description}".lower():
            score += 2
        return score, matched


def _request_bytes(url: str, timeout: float = 15.0) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AI-Engineer-Pathfinder/0.1 public-feed-reader"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_remotive(query: str, limit: int = 50, timeout: float = 15.0) -> list[JobLead]:
    """Read Remotive's public API, preserving the source URL for attribution."""
    query_string = urllib.parse.urlencode({"search": query, "limit": max(1, min(limit, 100))})
    payload = json.loads(_request_bytes(f"{REMOTIVE_API}?{query_string}").decode("utf-8"))
    return [JobLead.from_dict({"source": "Remotive", **record}) for record in payload.get("jobs", [])]


def _xml_value(item: ET.Element, name: str) -> str:
    node = item.find(name)
    return "" if node is None or node.text is None else node.text.strip()


def fetch_wwr(feed_url: str = WWR_PROGRAMMING_FEED, timeout: float = 15.0) -> list[JobLead]:
    """Read a public We Work Remotely RSS feed."""
    root = ET.fromstring(_request_bytes(feed_url, timeout))
    leads: list[JobLead] = []
    for item in root.findall(".//item"):
        leads.append(
            JobLead(
                source="We Work Remotely",
                title=_xml_value(item, "title"),
                company="",
                url=_xml_value(item, "link"),
                published=_xml_value(item, "pubDate"),
                description=_plain_text(_xml_value(item, "description")),
            )
        )
    return leads


def load_leads(path: Path) -> list[JobLead]:
    """Load a deterministic local fixture or previously saved lead file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("jobs", payload) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("Career lead file must contain a JSON list or a jobs list.")
    return [JobLead.from_dict(record) for record in records]


def filter_and_rank(
    leads: Iterable[JobLead],
    query: str = "",
    exclude_terms: Iterable[str] = (),
    engineering_only: bool = False,
    contract_first: bool = False,
) -> list[tuple[int, list[str], JobLead]]:
    """Filter by query terms and return highest-scoring leads first."""
    query_terms = [term.lower() for term in re.findall(r"[\w+#.-]+", query) if len(term) > 2]
    ranked: list[tuple[int, list[str], JobLead]] = []
    seen: set[str] = set()
    for lead in leads:
        identity = lead.url or f"{lead.source}|{lead.title}|{lead.company}"
        if identity in seen:
            continue
        seen.add(identity)
        haystack = f"{lead.title} {lead.company} {lead.location} {lead.description}".lower()
        if query_terms and not all(term in haystack for term in query_terms):
            continue
        if any(term.lower() in lead.title.lower() for term in exclude_terms):
            continue
        title = lead.title.lower()
        if any(term in title for term in NON_ENGINEERING_TITLE_TERMS):
            continue
        if engineering_only and not any(term in title for term in ENGINEERING_TITLE_TERMS):
            continue
        if contract_first and any(term in haystack for term in SCREENING_TERMS):
            continue
        score, matched = lead.score()
        if contract_first and any(term in haystack for term in CONTRACT_TERMS):
            score += 5
            matched.append("contract-friendly")
        ranked.append((score, matched, lead))
    return sorted(ranked, key=lambda item: (-item[0], item[2].title.lower(), item[2].company.lower()))


def draft_application(lead: JobLead, public_label: str = "Quiet Systems") -> str:
    """Create a truthful, non-submitting application draft."""
    company = lead.company or "the hiring team"
    role = lead.title or "the engineering role"
    return (
        f"Subject: Application — {role}\n\n"
        f"Hello {company} team,\n\n"
        f"I am an AI master's student and Python engineer interested in {role}. "
        "I build small, testable systems around APIs, retrieval, automation, "
        "and evaluation, with clear documentation of limitations.\n\n"
        "My current portfolio includes a dependency-free Python application, "
        "a tested skill-planning CLI, and an interactive browser demonstration. "
        f"I present that work under the public project label {public_label}.\n\n"
        "I would be glad to discuss the smallest useful contribution I could "
        "ship for this role. Portfolio: [insert public link]\n\n"
        "Regards,\n"
        f"{public_label}\n"
    )


def _safe_filename(value: str) -> str:
    """Make a short filesystem-safe label for a generated draft."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return cleaned[:70] or "untitled-role"


def write_drafts(
    ranked: Iterable[tuple[int, list[str], JobLead]],
    directory: Path,
    limit: int = 3,
    public_label: str = "Quiet Systems",
) -> list[Path]:
    """Write local drafts for the highest-ranked leads; never send them."""
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for index, (_, _, lead) in enumerate(list(ranked)[: max(limit, 0)], start=1):
        path = directory / f"{index:02d}-{_safe_filename(lead.company or 'company')}-{_safe_filename(lead.title)}.md"
        body = f"# Application draft\n\nSource: {lead.source}\nListing: {lead.url}\n\n{draft_application(lead, public_label)}"
        path.write_text(body, encoding="utf-8")
        written.append(path)
    return written


def _lead_key(lead: JobLead) -> str:
    return lead.url or f"{lead.source}|{lead.company}|{lead.title}"


def update_history(
    ranked: Iterable[tuple[int, list[str], JobLead]],
    path: Path,
) -> list[tuple[int, list[str], JobLead]]:
    """Record current listings and return only listings not seen previously."""
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {}
    seen = payload.get("seen", {})
    if not isinstance(seen, dict):
        seen = {}

    now = datetime.now(timezone.utc).isoformat()
    new_items: list[tuple[int, list[str], JobLead]] = []
    for score, matched, lead in ranked:
        key = _lead_key(lead)
        previous = seen.get(key)
        seen[key] = {
            "title": lead.title,
            "company": lead.company,
            "url": lead.url,
            "source": lead.source,
            "first_seen": previous.get("first_seen", now) if isinstance(previous, dict) else now,
            "last_seen": now,
        }
        if previous is None:
            new_items.append((score, matched, lead))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"updated_at": now, "seen": seen}, indent=2) + "\n",
        encoding="utf-8",
    )
    return new_items


def write_digest(
    ranked: Iterable[tuple[int, list[str], JobLead]],
    path: Path,
    draft_paths: Iterable[Path] = (),
) -> None:
    """Write a concise local queue for review without contacting anyone."""
    rows = list(ranked)
    drafts = list(draft_paths)
    lines = [
        "# Quiet Systems career digest",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"New leads: {len(rows)}",
        "",
    ]
    if not rows:
        lines.append("No new matching leads in this run.")
    for index, (score, matched, lead) in enumerate(rows, start=1):
        company = f" — {lead.company}" if lead.company else ""
        draft = drafts[index - 1] if index <= len(drafts) else None
        draft_line = f"- Draft: {draft}" if draft else "- Draft: not generated"
        lines.extend(
            [
                f"## {index}. {lead.title}{company}",
                f"- Score: {score}",
                f"- Source: {lead.source}",
                f"- Listing: {lead.url}",
                f"- Matched: {', '.join(matched) or 'general engineering terms'}",
                draft_line,
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
