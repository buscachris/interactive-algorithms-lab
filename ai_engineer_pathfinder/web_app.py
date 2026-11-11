"""Dependency-free local web dashboard for Interactive Algorithms Lab."""

from __future__ import annotations

import argparse
import json
import os
import shlex
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .compute import write_compute_report
from .finance import money, write_fuel_report
from .income import write_income_bundle
from .monitor import run_monitor
from .payments import PaymentWebhookError, ingest_lemonsqueezy_event
from .planner import Pathfinder, default_data_path


DEFAULT_COMPLETED = {"python", "git"}


PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Interactive Algorithms Lab</title>
  <style>
    :root { color-scheme: dark; --bg: #10151f; --panel: #182232; --line: #2b3a52; --ink: #e9f0ff; --muted: #9db0cc; --accent: #79d4ff; --hot: #b6f36b; }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; font: 16px/1.5 system-ui, sans-serif; background: radial-gradient(circle at 15% 0%, #203d58, var(--bg) 42%); color: var(--ink); }
    main { max-width: 1120px; margin: 0 auto; padding: 36px 20px 64px; }
    header { display: flex; justify-content: space-between; gap: 24px; align-items: end; margin-bottom: 28px; }
    h1 { margin: 0; font-size: clamp(2rem, 5vw, 4rem); letter-spacing: -0.05em; }
    h2 { margin-top: 0; }
    .subtitle { color: var(--muted); max-width: 680px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .panel { background: color-mix(in srgb, var(--panel) 92%, transparent); border: 1px solid var(--line); border-radius: 18px; padding: 20px; box-shadow: 0 14px 40px #0003; }
    .wide { grid-column: 1 / -1; }
    .metric { font-size: 2.2rem; color: var(--hot); font-weight: 700; }
    .muted { color: var(--muted); }
    .skill { border-top: 1px solid var(--line); padding: 13px 0; }
    .skill:first-child { border-top: 0; padding-top: 0; }
    .skill-title { display: flex; justify-content: space-between; gap: 12px; font-weight: 700; }
    .tag { color: var(--accent); font-size: .82rem; white-space: nowrap; }
    code, input, button { font: inherit; }
    input { width: 100%; padding: 11px 12px; color: var(--ink); background: #0d1320; border: 1px solid var(--line); border-radius: 10px; }
    button { margin-top: 10px; padding: 10px 15px; color: #061018; background: var(--accent); border: 0; border-radius: 10px; font-weight: 700; cursor: pointer; }
    button:hover { filter: brightness(1.1); }
    #path { color: var(--hot); min-height: 28px; }
    .cli-panel { background: #0b111b; }
    .cli-output { min-height: 180px; max-height: 360px; overflow: auto; margin: 14px 0 0; padding: 15px; color: #dff7ff; background: #060a11; border: 1px solid var(--line); border-radius: 12px; white-space: pre-wrap; font: .9rem/1.55 ui-monospace, SFMono-Regular, Menlo, monospace; }
    .cli-form { display: flex; gap: 10px; align-items: center; margin-top: 12px; }
    .cli-form input { flex: 1; }
    .cli-form button { margin-top: 0; }
    footer { margin-top: 28px; color: var(--muted); font-size: .9rem; }
    @media (max-width: 700px) { header { display: block; } }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Interactive Algorithms Lab</h1>
        <p class="subtitle">A data-structures-and-algorithms project that turns prerequisite records into practical engineering learning paths.</p>
      </div>
    </header>
    <section class="grid">
      <article class="panel">
        <h2>Progress</h2>
        <div id="progress" class="metric">Loading…</div>
        <div class="muted">Baseline completed skills: Python and Git</div>
      </article>
      <article class="panel">
        <h2>Graph path</h2>
        <label for="target" class="muted">Target skill</label>
        <input id="target" value="portfolio" aria-label="Target skill ID">
        <button id="path-button">Find learning path</button>
        <p id="path"></p>
      </article>
      <article class="panel wide">
        <h2>Recommended next skills</h2>
        <div id="next">Loading…</div>
      </article>
      <article class="panel wide cli-panel">
        <h2>Local CLI agent</h2>
        <p class="muted">Type a command or describe what you want in plain language. This safe local agent can read workflow data, create a fixed-scope service packet, and trigger a public-feed monitor pass; it cannot send applications or messages.</p>
        <div id="cli-output" class="cli-output" role="log" aria-live="polite">Type <code>help</code> to see available commands.</div>
        <form id="cli-form" class="cli-form">
          <input id="cli-command" autocomplete="off" placeholder="Try: find new AI jobs or start everything" aria-label="Local CLI command">
          <button type="submit">Run</button>
        </form>
      </article>
      <article class="panel wide">
        <h2>Search the skill records</h2>
        <input id="query" placeholder="Try: deployment, statistics, or graph" aria-label="Search skills">
        <button id="search-button">Search</button>
        <div id="results" class="skill"></div>
      </article>
    </section>
    <footer>Python standard library only · hash table · graph · BFS queue · priority heap · OOP</footer>
  </main>
  <script>
    const completed = 'python,git';
    const el = id => document.getElementById(id);
    const card = skill => `<div class="skill"><div class="skill-title"><span>${skill.title}</span><span class="tag">${skill.category} · ${skill.importance}/10</span></div><div class="muted">${skill.description}</div><code>${skill.id}</code></div>`;
    async function get(path) { const response = await fetch(path); return response.json(); }
    async function dashboard() {
      const data = await get(`/api/dashboard?completed=${completed}`);
      el('progress').textContent = `${data.finished}/${data.total} · ${data.percentage.toFixed(0)}%`;
      el('next').innerHTML = data.next.map(card).join('');
    }
    async function findPath() {
      const target = encodeURIComponent(el('target').value.trim());
      const data = await get(`/api/path?target=${target}&completed=${completed}`);
      el('path').textContent = data.path.length ? data.path.map(skill => skill.title).join(' → ') : data.error;
    }
    async function search() {
      const query = encodeURIComponent(el('query').value.trim());
      const data = await get(`/api/search?q=${query}`);
      el('results').innerHTML = data.results.length ? data.results.map(card).join('') : '<span class="muted">No matching skills.</span>';
    }
    async function runCli(command) {
      const response = await fetch('/api/cli', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({command})});
      const data = await response.json();
      const output = el('cli-output');
      output.textContent += `\n$ ${command}\n${data.output || data.error || 'No output.'}\n`;
      output.scrollTop = output.scrollHeight;
    }
    el('path-button').addEventListener('click', findPath);
    el('search-button').addEventListener('click', search);
    el('cli-form').addEventListener('submit', event => {
      event.preventDefault();
      const command = el('cli-command').value.trim();
      if (!command) return;
      el('cli-command').value = '';
      runCli(command).catch(error => {
        el('cli-output').textContent += `\nCLI error: ${error}\n`;
      });
    });
    window.addEventListener('keydown', event => {
      if (event.key === '/' && document.activeElement !== el('cli-command')) {
        event.preventDefault();
        el('cli-command').focus();
      }
    });
    dashboard();
    findPath();
  </script>
</body>
</html>"""

WEBXR_PAGE = Path(__file__).with_name("webxr.html").read_text(encoding="utf-8")


def _skill_json(skill) -> dict[str, object]:
    return {
        "id": skill.id,
        "title": skill.title,
        "category": skill.category,
        "description": skill.description,
        "importance": skill.importance,
    }


def _completed(query: dict[str, list[str]]) -> set[str]:
    values = query.get("completed", [",".join(sorted(DEFAULT_COMPLETED))])
    return {item for value in values for item in value.split(",") if item}


def _browser_cli(pathfinder: Pathfinder, command: str) -> str:
    """Run a deliberately small, non-shell command set from the browser."""
    try:
        tokens = shlex.split(command.strip())
    except ValueError as exc:
        return f"Parse error: {exc}"
    if not tokens:
        return "Type help for commands."
    name = tokens[0].lower()
    known = {
        "help", "?", "dashboard", "status", "next", "path", "search", "compute", "capacity", "fuel", "balance", "budget", "finance", "payment", "payments",
        "services", "products", "offer", "intake", "income", "reminder",
        "reminders", "jobs", "digest", "monitor", "start",
    }
    if name not in known:
        plain = " ".join(tokens).casefold()
        if (
            "start everything" in plain
            or "start the income" in plain
            or "run the income" in plain
            or "start automation" in plain
            or "run everything" in plain
        ):
            name = "start"
        elif (
            ("find" in plain and ("job" in plain or "work" in plain or "opportunit" in plain))
            or "job monitor" in plain
            or "check for jobs" in plain
        ):
            name = "monitor"
        elif (
            "service packet" in plain
            or "income service" in plain
            or "prepare the offer" in plain
            or "set up a service" in plain
        ):
            name = "income"
        elif "offer" in plain or "what can i sell" in plain:
            name = "offer"
        elif "intake" in plain or "client questions" in plain:
            name = "intake"
        elif "what services" in plain or "what products" in plain or "product line" in plain:
            name = "services"
        elif "remind" in plain or "reminder" in plain:
            name = "reminder"
        elif "what should i learn" in plain or "next skill" in plain or "what next" in plain:
            name = "next"
        elif "status" in plain or "how are we doing" in plain:
            name = "status"
        elif (
            "compute" in plain
            or "capacity" in plain
            or "rent the gpu" in plain
            or "rent out the gpu" in plain
            or "can we host" in plain
        ):
            name = "compute"
        elif (
            "fuel" in plain
            or "budget" in plain
            or "balance" in plain
            or "how much can we spend" in plain
            or "how much can the machine use" in plain
        ):
            name = "fuel"
        elif "payment" in plain or "payout" in plain or "webhook" in plain:
            name = "payments"
        else:
            return "I can do that locally when you phrase it as a job search, income setup, service/product list, offer, intake, reminder, compute check, fuel budget, next skill, status, or 'start everything'. Type help."
    if name in {"help", "?"}:
        return "help | dashboard | next [limit] | path <skill-id> | search <text> | compute | fuel | payments | services | offer | intake | income | reminder | jobs | monitor | start"
    if name in {"dashboard", "status"}:
        finished, total, percentage = pathfinder.progress(DEFAULT_COMPLETED)
        return f"Progress: {finished}/{total} ({percentage:.0f}%)\nCompleted: {', '.join(sorted(DEFAULT_COMPLETED))}"
    if name == "next":
        try:
            limit = max(1, min(int(tokens[1]), 20)) if len(tokens) > 1 else 5
        except ValueError:
            return "Usage: next [limit]"
        return "\n".join(f"- {skill.id}: {skill.title} ({skill.importance}/10)" for skill in pathfinder.next_skills(DEFAULT_COMPLETED, limit))
    if name == "path":
        target = tokens[1] if len(tokens) > 1 else "portfolio"
        try:
            skills = pathfinder.path_to(target, DEFAULT_COMPLETED)
        except KeyError as exc:
            return f"Unknown skill: {exc}"
        return " -> ".join(skill.title for skill in skills) if skills else f"No path found to {target}."
    if name == "search":
        query = " ".join(tokens[1:]).strip()
        if not query:
            return "Usage: search <text>"
        results = pathfinder.catalog.search(query)
        return "\n".join(f"- {skill.id}: {skill.title}" for skill in results) or "No matching skills."
    if name in {"jobs", "digest"}:
        digest = Path("career_output/latest.md")
        if not digest.exists():
            return "No local digest yet. Run: monitor"
        return digest.read_text(encoding="utf-8")[-7000:]
    if name in {"offer", "intake"}:
        bundle = Path("income_output")
        if not (bundle / "offer.md").exists():
            write_income_bundle(bundle)
        filename = "offer.md" if name == "offer" else "intake.md"
        return (bundle / filename).read_text(encoding="utf-8")[-7000:]
    if name in {"services", "products"}:
        manifest = Path("product_line.json")
        if not manifest.exists():
            return "No local product line manifest found."
        data = json.loads(manifest.read_text(encoding="utf-8"))
        return "\n".join(
            f"- {item['name']} | {item['status']} | {item['price']}"
            for item in data.get("products", [])
        )
    if name == "income":
        bundle = Path("income_output")
        paths = write_income_bundle(bundle)
        return f"Income bundle ready: {bundle}\nClient assets: {len(paths)}\nReview offer.md and intake.md before using them."
    if name in {"compute", "capacity"}:
        report = write_compute_report(Path("compute_output"))
        status = "READY" if report.private_batch_ready else "CAUTION"
        gpu_status = "READY" if report.external_gpu_hosting_ready else "BLOCKED"
        return "\n".join(
            [
                f"Private batch/inference: {status}",
                f"External GPU hosting: {gpu_status}",
                f"CPU: {report.cpu_threads} threads | RAM available: {report.memory_available_gib} GiB | Disk free: {report.disk_free_gib} GiB",
                f"GPU: {report.gpu_name} ({report.gpu_memory})",
                "Report: compute_output/latest.md",
                *[f"Blocker: {blocker}" for blocker in report.blockers],
            ]
        )
    if name in {"fuel", "balance", "budget", "finance"}:
        summary = write_fuel_report(Path("finance_output"))
        return "\n".join(
            [
                f"Cleared revenue: {money(summary.cleared_revenue_cents)}",
                f"Cleared costs: {money(summary.cleared_cost_cents)}",
                f"Reserve: {money(summary.reserve_cents)}",
                f"Safe fuel budget: {money(summary.fuel_budget_cents)}",
                f"Pending/unverified net: {money(summary.pending_cents)}",
                "Automatic transfers: disabled until verified payment webhook and spending cap",
                "Report: finance_output/latest.md",
            ]
        )
    if name in {"payment", "payments"}:
        return "\n".join(
            [
                f"Lemon Squeezy webhook secret configured: {'yes' if os.environ.get('LEMONSQUEEZY_WEBHOOK_SECRET') else 'no'}",
                "Receiver: POST /api/payment-webhook (local-only until HTTPS is deliberately configured)",
                "Accepted events: signed paid USD order_created and order_refunded",
                "Ledger: finance_output/ledger.json",
                "Automatic transfers: disabled; explicit spending cap required",
            ]
        )
    if name in {"reminder", "reminders"}:
        log = Path("reminders.log")
        if not log.exists():
            return "Reminder scheduled for 2026-08-15 18:00 CDT: expand income services and evaluate the OpenAI Enterprise tier."
        return log.read_text(encoding="utf-8")[-4000:]
    if name == "monitor":
        result = run_monitor(Path("career_output"), notify=False)
        lines = [f"New leads: {result.new_leads}", f"Current matches: {result.total_matches}", "Digest: career_output/latest.md"]
        lines.extend(f"Warning: {error}" for error in result.errors)
        return "\n".join(lines)
    if name == "start":
        bundle = Path("income_output")
        paths = write_income_bundle(bundle)
        result = run_monitor(Path("career_output"), notify=False)
        compute = write_compute_report(Path("compute_output"))
        fuel = write_fuel_report(Path("finance_output"))
        lines = [
            "Income automation cycle started.",
            f"Service assets: {len(paths)} in income_output/",
            f"New leads: {result.new_leads}",
            f"Current matches: {result.total_matches}",
            f"Private compute pilot: {'ready' if compute.private_batch_ready else 'caution'}",
            f"Safe fuel budget: {money(fuel.fuel_budget_cents)}",
            "Review: income_output/offer.md, career_output/latest.md, compute_output/latest.md, and finance_output/latest.md",
        ]
        lines.extend(f"Warning: {error}" for error in result.errors)
        return "\n".join(lines)
    return f"Unknown command: {name}. Type help."


def make_handler(pathfinder: Pathfinder):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, payload: str, content_type: str = "text/html; charset=utf-8", status: int = 200) -> None:
            body = payload.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload: dict[str, object], status: int = 200) -> None:
            self._send(json.dumps(payload), "application/json; charset=utf-8", status)

        def do_POST(self) -> None:  # noqa: N802 - required HTTP server method name.
            parsed = urlparse(self.path)
            if parsed.path == "/api/payment-webhook":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = 0
                if length <= 0 or length > 262144:
                    self._json({"error": "invalid body length"}, status=413)
                    return
                raw_body = self.rfile.read(length)
                secret = os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")
                signature = self.headers.get("X-Signature", "")
                try:
                    result = ingest_lemonsqueezy_event(
                        raw_body,
                        signature,
                        secret,
                        Path("finance_output/ledger.json"),
                    )
                except PaymentWebhookError:
                    self._json({"error": "webhook rejected"}, status=401)
                    return
                self._json({"status": result})
                return
            if parsed.path != "/api/cli":
                self.send_error(404)
                return
            try:
                length = min(int(self.headers.get("Content-Length", "0")), 8192)
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                command = str(payload.get("command", ""))
                self._json({"output": _browser_cli(pathfinder, command)})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._json({"error": f"Invalid CLI request: {exc}"})

        def do_GET(self) -> None:  # noqa: N802 - required HTTP server method name.
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            if parsed.path == "/":
                self._send(PAGE)
                return
            if parsed.path in {"/webxr", "/webxr.html", "/xr"}:
                self._send(WEBXR_PAGE)
                return
            if parsed.path == "/api/dashboard":
                completed = _completed(query)
                finished, total, percentage = pathfinder.progress(completed)
                self._json({
                    "finished": finished,
                    "total": total,
                    "percentage": percentage,
                    "next": [_skill_json(skill) for skill in pathfinder.next_skills(completed)],
                })
                return
            if parsed.path == "/api/search":
                self._json({"results": [_skill_json(skill) for skill in pathfinder.catalog.search(query.get("q", [""])[0])]})
                return
            if parsed.path == "/api/path":
                target = query.get("target", ["portfolio"])[0]
                try:
                    path = pathfinder.path_to(target, _completed(query))
                except KeyError as exc:
                    self._json({"path": [], "error": str(exc)})
                    return
                self._json({"path": [_skill_json(skill) for skill in path]})
                return
            self.send_error(404)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Pathfinder browser dashboard.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    pathfinder = Pathfinder.from_json(default_data_path())
    server = ThreadingHTTPServer((args.host, args.port), make_handler(pathfinder))
    print(f"Interactive Algorithms Lab running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Pathfinder.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
