"""Build a privacy-sanitized distributable toolkit archive."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


PRODUCT_NAME = "Interactive Algorithms Lab Toolkit"
PRODUCT_VERSION = "0.2.0"


def _product_docs() -> dict[str, str]:
    return {
        "docs/QUICKSTART.md": """# Quickstart

From the extracted toolkit directory, run these commands with Python 3.10 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m ai_engineer_pathfinder
python -m ai_engineer_pathfinder career search --query \"AI engineer\" --entry-level --engineering-only
python -m ai_engineer_pathfinder career monitor --output ./career_output --notify
python -m ai_engineer_pathfinder income --output ./income_output
python -m ai_engineer_pathfinder compute --output ./compute_output
python -m ai_engineer_pathfinder finance --output ./finance_output
```

The online commands read public feeds only. They do not log in, submit
applications, send messages, or store credentials.
""",
        "docs/PRODUCT.md": """# Product description

Interactive Algorithms Lab Toolkit is a standard-library-first CLI for learning,
showing, and organizing practical AI-engineering work.

It includes:

- a searchable skill roadmap and prerequisite planner;
- tested data-structure demonstrations;
- public remote-lead ranking;
- contract-first proposal drafting;
- private AI workflow service templates;
- local compute-capacity reporting and private inference/batch service templates;
- optional signed payment-webhook ingestion for verified revenue accounting;
- local history and digest generation.
- a one-shot public-feed monitor with deduplication and optional local alerts.

It is a productivity and portfolio tool. It is not a promise of employment,
income, customer conversion, or perfectly accurate job matching.
""",
        "docs/PRIVACY.md": """# Privacy and release boundary

This release contains source code, generic examples, and placeholders only.

Before publishing a customized copy, remove:

- lead history and saved job listings;
- personal email, names, addresses, tokens, and hostnames;
- screenshots containing accounts or private data;
- local output directories and generated drafts.

Payment providers, employers, and contract platforms may require accurate legal
identity and tax information. A public project label does not replace those
requirements.
""",
        "docs/RELEASE_CHECKLIST.md": """# Release checklist

- [ ] Run the test suite.
- [ ] Review the archive file list.
- [ ] Confirm no personal data or credentials are present.
- [ ] Verify that `LICENSE` and `THIRD_PARTY_NOTICES.md` match the source.
- [ ] Create the storefront under the intended legal/payment identity.
- [ ] Upload the archive and test a clean customer download.
- [ ] Keep a free README/demo so buyers can evaluate the fit.
""",
        "store_page_draft.md": """# Store page draft

## Interactive Algorithms Lab Toolkit

A privacy-conscious CLI for turning algorithms study and engineering
workflow into repeatable, testable action.

### Includes

- skill roadmap and prerequisite planner;
- tested Python examples;
- public-lead ranking and contract-first filters;
- proposal and client-workflow templates;
- local history, drafts, and review digests.

### Price experiment

Suggested first test: **$29 one-time** for the toolkit. An optional **$9/month
update tier** could provide refreshed templates and feed rules, but recurring
support should only be offered if updates are actually maintained.

### Honest boundary

This tool organizes work and reduces repetitive preparation. It does not
guarantee jobs, clients, sales, or income.
""",
    }


def build_release(output_zip: Path, version: str = PRODUCT_VERSION) -> tuple[Path, Path, list[str]]:
    """Build an archive from known project files and return archive metadata."""
    project_root = Path(__file__).resolve().parents[1]
    root_name = f"interactive-algorithms-lab-toolkit-{version}"
    selected = [
        project_root / "README.md",
        project_root / "LICENSE",
        project_root / "THIRD_PARTY_NOTICES.md",
        project_root / "VERIFICATION.md",
        project_root / "docs/screenshots/skill-dashboard.png",
        project_root / "pyproject.toml",
        project_root / "ai_engineer_pathfinder/webxr.html",
    ]
    selected.extend(sorted((project_root / "ai_engineer_pathfinder").glob("*.py")))
    selected.append(project_root / "data" / "skills.json")
    selected.append(project_root / "product_line.json")
    selected.extend(sorted((project_root / "tests").glob("*.py")))

    files: dict[str, bytes] = {}
    for path in selected:
        relative = path.relative_to(project_root).as_posix()
        files[relative] = path.read_bytes()
    for relative, content in _product_docs().items():
        files[relative] = content.encode("utf-8")

    manifest = {
        "name": PRODUCT_NAME,
        "version": version,
        "files": sorted(files),
        "privacy": "sanitized-template-release",
    }
    files["MANIFEST.json"] = json.dumps(manifest, indent=2).encode("utf-8") + b"\n"

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in sorted(files):
            archive.writestr(f"{root_name}/{relative}", files[relative])

    digest = hashlib.sha256(output_zip.read_bytes()).hexdigest()
    manifest_path = output_zip.with_suffix(".manifest.json")
    manifest["sha256"] = digest
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output_zip, manifest_path, sorted(files)
