#!/usr/bin/env python3
"""One-command local demo launcher for AIDEFEND Discovery."""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = ROOT / ".venv"
REVIEW_CONSOLE = ROOT / "review_console"
REQUIREMENTS = ROOT / "requirements.txt"
SAMPLE_REPORT = ROOT / "tests" / "fixtures" / "sample_gap_run.json"
REVIEW_DB = ROOT / "lab" / "aidefend_discovery" / "review_console.db"


def log(message: str) -> None:
    print(f"[demo] {message}", flush=True)


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"ERROR: required tool not found on PATH: {name}")
    return path


def python_bin() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv(skip_install: bool) -> Path:
    py = python_bin()
    if not py.exists():
        log(f"creating Python virtual environment at {VENV_DIR}")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    if not skip_install:
        stamp = VENV_DIR / ".aidefend-demo-deps"
        needs_install = not stamp.exists()
        if REQUIREMENTS.exists() and stamp.exists():
            needs_install = REQUIREMENTS.stat().st_mtime > stamp.stat().st_mtime
        if needs_install:
            log("installing Python requirements")
            subprocess.check_call([str(py), "-m", "pip", "install", "-r", str(REQUIREMENTS)], cwd=ROOT)
            stamp.write_text(str(time.time()), encoding="utf-8")
    return py


def ensure_frontend(skip_install: bool) -> None:
    require_tool("node")
    require_tool("npm")
    if not skip_install and not (REVIEW_CONSOLE / "node_modules").exists():
        log("installing frontend dependencies")
        subprocess.check_call(["npm", "ci"], cwd=REVIEW_CONSOLE)
    log("building frontend")
    subprocess.check_call(["npm", "run", "build"], cwd=REVIEW_CONSOLE)


def find_port(start: int) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise SystemExit("ERROR: could not find a free local port")


def wait_for_server(url: str, timeout_s: float = 20.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/run", timeout=1.0) as response:
                return 200 <= response.status < 500
        except OSError:
            time.sleep(0.25)
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Start the AIDEFEND Discovery local demo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true", help="Do not auto-open the browser")
    parser.add_argument("--skip-install", action="store_true", help="Skip dependency installation checks")
    args = parser.parse_args(argv)

    require_tool("python3")
    py = ensure_venv(args.skip_install)
    ensure_frontend(args.skip_install)
    port = find_port(args.port)
    url = f"http://{args.host}:{port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "scripts")

    command = [
        str(py),
        "-m",
        "aidefend_discovery.review_console",
        "--report",
        str(SAMPLE_REPORT),
        "--db",
        str(REVIEW_DB),
        "--port",
        str(port),
        "--host",
        args.host,
    ]
    log(f"starting local demo at {url}")
    proc = subprocess.Popen(command, cwd=ROOT, env=env)
    try:
        if wait_for_server(url):
            log(f"ready: {url}")
            if not args.no_open:
                opened = webbrowser.open(url)
                if not opened:
                    log(f"browser auto-open unavailable. Open {url}")
        else:
            log(f"server did not respond yet. Open {url} after startup completes.")
        proc.wait()
    except KeyboardInterrupt:
        log("stopping demo")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return 0
    return proc.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
