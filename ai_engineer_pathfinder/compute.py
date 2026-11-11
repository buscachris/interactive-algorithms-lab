"""Local compute-capacity checks for a privacy-conscious AI service workflow."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ComputeReport:
    host: str
    system: str
    cpu_threads: int
    memory_total_gib: float
    memory_available_gib: float
    disk_free_gib: float
    gpu_detected: bool
    gpu_name: str
    gpu_memory: str
    gpu_driver_ready: bool
    gpu_error: str
    private_batch_ready: bool
    external_gpu_hosting_ready: bool
    blockers: tuple[str, ...]


def _gib(value: int) -> float:
    return round(value / (1024**3), 1)


def _memory() -> tuple[float, float]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            key, raw = line.split(":", 1)
            values[key] = int(raw.strip().split()[0]) * 1024
    except (FileNotFoundError, ValueError):
        return 0.0, 0.0
    return _gib(values.get("MemTotal", 0)), _gib(values.get("MemAvailable", 0))


def _gpu() -> tuple[bool, str, str, bool, str]:
    command = shutil.which("nvidia-smi")
    if command:
        try:
            result = subprocess.run(
                [
                    command,
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                name, _, memory = result.stdout.strip().splitlines()[0].partition(",")
                return True, name.strip(), f"{memory.strip()} MiB", True, ""
            error = result.stderr.strip() or "nvidia-smi returned no GPU data"
            return True, "NVIDIA GPU detected by tool", "unknown", False, error
        except (OSError, subprocess.SubprocessError) as exc:
            return True, "NVIDIA GPU detected by tool", "unknown", False, str(exc)

    lspci = shutil.which("lspci")
    if lspci:
        try:
            result = subprocess.run([lspci], check=False, capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if any(token in line.casefold() for token in ("vga", "3d", "display")):
                    return True, line.split(": ", 1)[-1], "unknown", False, "nvidia-smi is not available"
        except (OSError, subprocess.SubprocessError):
            pass
    return False, "none detected", "0", False, "No supported GPU inventory was found"


def collect_compute_report() -> ComputeReport:
    total, available = _memory()
    disk = shutil.disk_usage(Path.home())
    gpu_detected, gpu_name, gpu_memory, driver_ready, gpu_error = _gpu()
    blockers: list[str] = []
    if disk.free < 50 * 1024**3:
        blockers.append(f"Only {_gib(disk.free)} GiB free on the home filesystem; free storage before hosting workloads")
    if gpu_detected and not driver_ready:
        blockers.append("GPU driver is not ready; do not advertise GPU capacity yet")
    if not gpu_detected:
        blockers.append("No supported GPU was detected")
    private_batch_ready = available >= 8.0 and disk.free >= 20 * 1024**3
    external_gpu_hosting_ready = gpu_detected and driver_ready and disk.free >= 50 * 1024**3
    if not private_batch_ready:
        blockers.append("Private batch capacity is below the conservative local threshold")
    return ComputeReport(
        host=platform.node(),
        system=f"{platform.system()} {platform.machine()}",
        cpu_threads=os.cpu_count() or 1,
        memory_total_gib=total,
        memory_available_gib=available,
        disk_free_gib=_gib(disk.free),
        gpu_detected=gpu_detected,
        gpu_name=gpu_name,
        gpu_memory=gpu_memory,
        gpu_driver_ready=driver_ready,
        gpu_error=gpu_error,
        private_batch_ready=private_batch_ready,
        external_gpu_hosting_ready=external_gpu_hosting_ready,
        blockers=tuple(blockers),
    )


def write_compute_report(output_dir: Path) -> ComputeReport:
    report = collect_compute_report()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "latest.json").write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
    status = "READY" if report.private_batch_ready else "CAUTION"
    gpu_status = "READY" if report.external_gpu_hosting_ready else "BLOCKED"
    lines = [
        f"# Compute capacity — {report.host}",
        "",
        f"- System: {report.system}",
        f"- CPU threads: {report.cpu_threads}",
        f"- Memory: {report.memory_available_gib} GiB available / {report.memory_total_gib} GiB total",
        f"- Home filesystem: {report.disk_free_gib} GiB free",
        f"- GPU: {report.gpu_name} ({report.gpu_memory})",
        f"- Private batch/inference pilot: **{status}**",
        f"- External GPU hosting: **{gpu_status}**",
        "",
        "## Guardrails",
        "",
        "This report is a capacity check, not permission to expose the machine. Do not accept arbitrary customer code, secrets, or inbound network traffic until isolation, authentication, storage, backup, and pricing are reviewed.",
    ]
    if report.gpu_error:
        lines.extend(["", f"GPU diagnostic: {report.gpu_error}"])
    if report.blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in report.blockers)
    (output_dir / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
