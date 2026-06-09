import os
import shutil
import signal
import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import psutil

from config import settings

# In-memory process registry; keyed by bench name
_PROCESSES: dict[str, subprocess.Popen] = {}
_PID_FILE = Path(settings.bench_root) / ".bench_manager_pids.json"


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def _load_pids() -> dict:
    if _PID_FILE.exists():
        try:
            return json.loads(_PID_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_pids() -> None:
    pids = {name: proc.pid for name, proc in _PROCESSES.items() if proc.poll() is None}
    _PID_FILE.write_text(json.dumps(pids))


# ---------------------------------------------------------------------------
# Bench discovery
# ---------------------------------------------------------------------------

def is_bench_dir(path: Path) -> bool:
    return (
        path.is_dir()
        and (path / "Procfile").exists()
        and (path / "apps").exists()
        and (path / "sites").exists()
    )


def bench_exe(bench_path: Path) -> str:
    # 0. Explicit override from config / .env
    if settings.bench_cmd:
        return settings.bench_cmd

    # 1. bench's own virtualenv — standard layout (most reliable, avoids PATH issues)
    local = bench_path / "env" / "bin" / "bench"
    if local.exists():
        return str(local)

    # 1b. non-standard layout where the bench dir itself is the venv
    local_flat = bench_path / "bin" / "bench"
    if local_flat.exists():
        return str(local_flat)

    # 2. bench in PATH — includes directories added by pyenv/nvm/etc.
    found = shutil.which("bench")
    if found:
        return found

    # 3. Common install locations on macOS / Linux
    candidates = [
        Path.home() / ".local" / "bin" / "bench",
        Path("/opt/homebrew/bin/bench"),
        Path("/usr/local/bin/bench"),
        Path("/usr/bin/bench"),
    ]
    # macOS: pip install --user puts binaries under ~/Library/Python/X.Y/bin/
    library_python = Path.home() / "Library" / "Python"
    if library_python.exists():
        for ver_dir in sorted(library_python.iterdir(), reverse=True):
            candidates.append(ver_dir / "bin" / "bench")

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    raise FileNotFoundError(
        f"Cannot find 'bench' for {bench_path.name}. "
        "Set BENCH_MANAGER_BENCH_CMD=/path/to/bench in .env, "
        "or ensure 'bench' is on PATH."
    )


@dataclass
class BenchInfo:
    name: str
    path: str
    status: str  # running | stopped
    apps: list = field(default_factory=list)
    sites: list = field(default_factory=list)
    frappe_version: str = ""
    python_path: str = ""
    port: int = 0

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}" if self.port else ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "status": self.status,
            "apps": self.apps,
            "sites": self.sites,
            "frappe_version": self.frappe_version,
            "port": self.port,
            "url": self.url,
        }


def _get_apps(bench_path: Path) -> list[str]:
    apps_dir = bench_path / "apps"
    if not apps_dir.exists():
        return []
    return sorted(
        d.name for d in apps_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def _get_sites(bench_path: Path) -> list[str]:
    sites_dir = bench_path / "sites"
    if not sites_dir.exists():
        return []
    return sorted(
        d.name for d in sites_dir.iterdir()
        if d.is_dir()
        and not d.name.startswith(".")
        and d.name not in ("assets",)
        and (d / "site_config.json").exists()
    )


def _get_port(bench_path: Path) -> int:
    import re

    # 1. Procfile web line: bench serve --port 8000
    procfile = bench_path / "Procfile"
    if procfile.exists():
        for line in procfile.read_text().splitlines():
            if line.startswith("web:"):
                m = re.search(r"--port\s+(\d+)", line)
                if m:
                    return int(m.group(1))

    # 2. common_site_config.json webserver_port
    common_cfg = bench_path / "sites" / "common_site_config.json"
    if common_cfg.exists():
        try:
            cfg = json.loads(common_cfg.read_text())
            port = cfg.get("webserver_port")
            if port:
                return int(port)
        except Exception:
            pass

    return 0


def _get_frappe_version(bench_path: Path) -> str:
    for candidate in [
        bench_path / "apps" / "frappe" / "frappe" / "__version__.py",
        bench_path / "apps" / "frappe" / "frappe" / "_version.py",
    ]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                if "__version__" in line and "=" in line:
                    return line.split("=")[-1].strip().strip("\"'")
    return ""


def _process_running(bench_path: Path, extra_pid: Optional[int] = None) -> bool:
    if extra_pid:
        try:
            p = psutil.Process(extra_pid)
            if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                return True
        except psutil.NoSuchProcess:
            pass

    bench_str = str(bench_path)
    for proc in psutil.process_iter(["pid", "cwd", "cmdline"]):
        try:
            cwd = proc.info.get("cwd") or ""
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if cwd.startswith(bench_str) and any(
                kw in cmdline for kw in ("honcho", "gunicorn", "frappe serve", "frappe worker")
            ):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def get_bench_status(bench_name: str) -> str:
    bench_path = Path(settings.bench_root) / bench_name

    proc = _PROCESSES.get(bench_name)
    if proc is not None:
        if proc.poll() is None:
            return "running"
        del _PROCESSES[bench_name]

    # Check persisted PIDs from a previous server run
    saved = _load_pids()
    saved_pid = saved.get(bench_name)
    if _process_running(bench_path, saved_pid):
        return "running"

    return "stopped"


def get_bench_info(bench_path: Path) -> BenchInfo:
    return BenchInfo(
        name=bench_path.name,
        path=str(bench_path),
        status=get_bench_status(bench_path.name),
        apps=_get_apps(bench_path),
        sites=_get_sites(bench_path),
        frappe_version=_get_frappe_version(bench_path),
        python_path=str(bench_path / "env" / "bin" / "python"),
        port=_get_port(bench_path),
    )


def discover_benches() -> list[BenchInfo]:
    root = Path(settings.bench_root)
    if not root.exists():
        return []
    return [
        get_bench_info(p)
        for p in sorted(root.iterdir())
        if is_bench_dir(p)
    ]


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def _kill_bench_processes(bench_path: Path, sig: signal.Signals) -> bool:
    """Send `sig` to all processes associated with this bench. Returns True if anything was killed."""
    bench_str = str(bench_path)
    killed = False
    for p in psutil.process_iter(["pid", "cwd", "cmdline"]):
        try:
            cwd = p.info.get("cwd") or ""
            cmdline = " ".join(p.info.get("cmdline") or [])
            # Match any process whose cwd is inside this bench dir
            if not cwd.startswith(bench_str):
                continue
            if any(kw in cmdline for kw in (
                "honcho", "gunicorn", "frappe", "redis-server", "node"
            )):
                p.send_signal(sig)
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed


def _get_redis_ports(bench_path: Path) -> list[int]:
    """Read Redis ports from the bench config files."""
    import re
    ports = []
    for conf in (bench_path / "config").glob("redis_*.conf"):
        try:
            text = conf.read_text()
            m = re.search(r"^\s*port\s+(\d+)", text, re.MULTILINE)
            if m:
                ports.append(int(m.group(1)))
        except Exception:
            pass
    return ports


def _wait_port_free(port: int, timeout: float = 8.0) -> bool:
    """Block until the port is no longer in use, or timeout expires."""
    import socket, time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return True  # port is free
        time.sleep(0.4)
    return False  # timed out


def _honcho_exe(bench_path: Path) -> Optional[str]:
    """Return the honcho executable, searching bench env, PATH, and ~/Library/Python."""
    candidates: list[Path] = [
        bench_path / "env" / "bin" / "honcho",
        bench_path / "bin" / "honcho",
    ]

    # macOS ~/Library/Python/X.Y/bin — where pip install --user puts things
    library_python = Path.home() / "Library" / "Python"
    if library_python.exists():
        for ver_dir in sorted(library_python.iterdir(), reverse=True):
            candidates.append(ver_dir / "bin" / "honcho")

    candidates += [
        Path.home() / ".local" / "bin" / "honcho",
        Path("/opt/homebrew/bin/honcho"),
        Path("/usr/local/bin/honcho"),
    ]

    for c in candidates:
        if c.exists():
            return str(c)

    # Last resort: PATH lookup
    found = shutil.which("honcho")
    return found if found else None


def _pip_for_bench(bench_path: Path) -> Optional[str]:
    """Find the pip that corresponds to this bench's Python environment."""
    # 1. Bench's own virtualenv pip
    local_pip = bench_path / "env" / "bin" / "pip"
    if local_pip.exists():
        return str(local_pip)

    # 2. Same pip as the bench CLI (e.g. ~/Library/Python/3.9/bin/pip)
    exe = None
    try:
        exe = bench_exe(bench_path)
    except FileNotFoundError:
        pass
    if exe:
        pip_sibling = Path(exe).parent / "pip"
        if pip_sibling.exists():
            return str(pip_sibling)
        pip3_sibling = Path(exe).parent / "pip3"
        if pip3_sibling.exists():
            return str(pip3_sibling)

    return shutil.which("pip3") or shutil.which("pip")


def install_honcho(bench_name: str) -> dict:
    """Install honcho using the pip that matches this bench's Python."""
    bench_path = Path(settings.bench_root) / bench_name
    pip = _pip_for_bench(bench_path)
    if not pip:
        return {"success": False, "error": "Cannot find pip to install honcho."}

    result = subprocess.run(
        [pip, "install", "honcho"],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return {"success": True}
    return {"success": False, "error": result.stderr or result.stdout}


def start_bench(bench_name: str) -> dict:
    import time, tempfile
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        return {"success": False, "error": "Not a valid bench directory"}
    if get_bench_status(bench_name) == "running":
        return {"success": False, "error": "Bench is already running"}

    try:
        exe = bench_exe(bench_path)
    except FileNotFoundError as e:
        return {"success": False, "error": str(e)}

    # Use honcho directly — avoids `bench start` doing a PATH-based which("honcho")
    honcho = _honcho_exe(bench_path)
    if not honcho:
        return {
            "success": False,
            "error": (
                "honcho is not installed. "
                "Click 'Install honcho' below, then try starting again."
            ),
            "missing_honcho": True,
        }

    # Build an env that adds the bench CLI dir and the bench's own venv/bin to PATH
    # so that Procfile commands like "bench serve", "bench worker" resolve correctly.
    launch_env = os.environ.copy()
    extra_paths: list[str] = []
    try:
        extra_paths.append(str(Path(exe).parent))       # dir containing bench binary
    except Exception:
        pass
    venv_bin = bench_path / "env" / "bin"
    if venv_bin.exists():
        extra_paths.append(str(venv_bin))               # bench's own virtualenv
    if extra_paths:
        launch_env["PATH"] = ":".join(extra_paths) + ":" + launch_env.get("PATH", "")

    # Capture stderr to a temp file so we can report the real error on failure
    stderr_file = tempfile.NamedTemporaryFile(delete=False, suffix=".log")
    try:
        proc = subprocess.Popen(
            [honcho, "start", "-f", str(bench_path / "Procfile")],
            cwd=str(bench_path),
            stdout=subprocess.DEVNULL,
            stderr=stderr_file,
            start_new_session=True,
            env=launch_env,
        )
    finally:
        stderr_file.close()

    _PROCESSES[bench_name] = proc
    _save_pids()

    # Wait briefly — detect immediate exits (port conflict, bad config, etc.)
    time.sleep(2)
    if proc.poll() is not None:
        _PROCESSES.pop(bench_name, None)
        _save_pids()
        try:
            error_detail = Path(stderr_file.name).read_text().strip()
            lines = [l.strip() for l in error_detail.splitlines() if l.strip()]
            noise = ("INFO:", "WARNING:", "NotOpenSSLWarning", "warn(", "site-packages")
            clean = [l for l in lines if not any(n in l for n in noise)]
            # Return up to last 5 meaningful lines so the UI shows full context
            error_msg = "\n".join(clean[-5:]) if clean else f"exited with code {proc.returncode}"
        except Exception:
            error_msg = f"exited with code {proc.returncode}"
        finally:
            Path(stderr_file.name).unlink(missing_ok=True)
        return {"success": False, "error": error_msg}

    Path(stderr_file.name).unlink(missing_ok=True)
    return {"success": True, "pid": proc.pid}


def stop_bench(bench_name: str) -> dict:
    import time
    bench_path = Path(settings.bench_root) / bench_name
    port = _get_port(bench_path)

    # 1. Kill the tracked honcho process group first
    proc = _PROCESSES.pop(bench_name, None)
    if proc is not None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    # 2. SIGKILL any remaining bench processes (gunicorn workers, redis, scheduler, etc.)
    _kill_bench_processes(bench_path, signal.SIGKILL)

    # 3. Port-based kill: forcibly kill anything still listening on bench ports
    all_ports = _get_redis_ports(bench_path)
    if port:
        all_ports.append(port)
    for conn in psutil.net_connections(kind="inet"):
        try:
            if conn.laddr.port in all_ports and conn.status == "LISTEN" and conn.pid:
                psutil.Process(conn.pid).kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    _save_pids()

    # 4. Wait for all ports to be released before returning
    for p in all_ports:
        _wait_port_free(p, timeout=8.0)

    return {"success": True}


def create_bench_process(name: str, frappe_branch: str = "version-15") -> subprocess.Popen:
    parent = Path(settings.bench_root)
    target = parent / name
    if target.exists():
        raise ValueError(f"Directory '{name}' already exists in {parent}")

    # Use system bench CLI for init; it uses its own virtualenv internally
    return subprocess.Popen(
        ["bench", "init", "--frappe-branch", frappe_branch, name],
        cwd=str(parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def delete_bench(bench_name: str) -> dict:
    import shutil

    bench_path = Path(settings.bench_root) / bench_name
    if not bench_path.exists():
        return {"success": False, "error": "Bench not found"}
    if not is_bench_dir(bench_path):
        return {"success": False, "error": "Not a valid bench directory"}

    stop_bench(bench_name)
    shutil.rmtree(str(bench_path))
    return {"success": True}
