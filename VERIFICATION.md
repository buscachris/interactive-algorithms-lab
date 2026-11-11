# Verification

This file records the current evidence boundary for Interactive Algorithms Lab.

## Previously recorded evidence

- Python test suite: `40/40` tests passed.
- Python syntax check: all package modules compile with `py_compile`.
- CLI smoke check: dashboard starts and reports the skill graph baseline.
- Product archive test: sanitized release archive generation passes.
- Browser route coverage: local dashboard handler and WebXR page tests pass.
- WebXR lab: desktop fallback, station controls, data-structure demonstrations,
  and immersive-mode code paths are present in `ai_engineer_pathfinder/webxr.html`.
- MIT license for original project files: `LICENSE`.
- Third-party dependency boundary: `THIRD_PARTY_NOTICES.md`.

## Not yet verified

- Headset-specific immersive WebXR behavior on target hardware.
- Production deployment or hosted HTTPS behavior.
- External job-feed availability during a live network run.
- Customer revenue, employment outcomes, or production customer deployments.

## Reproduce

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile ai_engineer_pathfinder/*.py
python3 -m ai_engineer_pathfinder
python3 -m ai_engineer_pathfinder.web_app --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/webxr` for the browser lab after starting the
dashboard. The Python package path remains `ai_engineer_pathfinder` for
backward-compatible CLI and import commands; the public project name is
Interactive Algorithms Lab.

## Source export checks — 2026-11-11

- `python3 -m unittest discover -s tests -v`: **42 tests passed** on the isolated source snapshot.
- `python3 -m ai_engineer_pathfinder`: passed; displayed the 2/15 baseline and recommendations without network access.
- Python syntax and JSON parsing passed. Source hashes, selected file list and credential-pattern checks passed.
- Tests cover fixtures and handler construction; they do not establish live browser, payment-provider or external-feed behavior.
- The generated product ZIP is not a complete release: the current builder selects Python modules but omits the browser HTML, LICENSE and third-party notices. Prepare and validate a complete release package before distributing that archive. The source repository contains those files.
