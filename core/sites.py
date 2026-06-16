import dataclasses
import json
import platform
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from core.bench import bench_exe


@dataclass
class SiteInfo:
    name: str
    bench: str
    installed_apps: list = field(default_factory=list)
    db_name: str = ""
    db_type: str = "mariadb"

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def list_sites(bench_path: Path) -> list[SiteInfo]:
    sites_dir = bench_path / "sites"
    if not sites_dir.exists():
        return []
    result = []
    for d in sorted(sites_dir.iterdir()):
        config_file = d / "site_config.json"
        if d.is_dir() and not d.name.startswith(".") and config_file.exists():
            result.append(get_site_info(bench_path, d.name))
    return result


def get_site_info(bench_path: Path, site_name: str) -> SiteInfo:
    config_file = bench_path / "sites" / site_name / "site_config.json"
    apps_txt = bench_path / "sites" / site_name / "apps.txt"

    db_name = ""
    db_type = "mariadb"
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text())
            db_name = cfg.get("db_name", "")
            db_type = cfg.get("db_type", "mariadb")
        except Exception:
            pass

    apps: list[str] = []
    if apps_txt.exists():
        apps = [a.strip() for a in apps_txt.read_text().splitlines() if a.strip()]

    return SiteInfo(
        name=site_name,
        bench=bench_path.name,
        installed_apps=apps,
        db_name=db_name,
        db_type=db_type,
    )


def create_site_process(
    bench_path: Path,
    site_name: str,
    admin_password: str,
    db_name: str | None = None,
    db_root_password: str | None = None,
) -> subprocess.Popen:
    exe = bench_exe(bench_path)
    cmd = [exe, "new-site", site_name, f"--admin-password={admin_password}"]
    if db_name:
        cmd += [f"--db-name={db_name}"]
    if db_root_password:
        cmd += [f"--mariadb-root-password={db_root_password}"]

    return subprocess.Popen(
        cmd,
        cwd=str(bench_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def drop_site(
    bench_path: Path, site_name: str, force: bool = True, root_password: str = ""
) -> dict:
    exe = bench_exe(bench_path)
    cmd = [exe, "drop-site", site_name]
    if force:
        cmd.append("--force")
    if root_password:
        cmd += ["--root-password", root_password]
    result = subprocess.run(cmd, cwd=str(bench_path), capture_output=True, text=True)
    if result.returncode == 0:
        return {"success": True}
    return {"success": False, "error": result.stderr or result.stdout}


def use_site(bench_path: Path, site_name: str) -> dict:
    exe = bench_exe(bench_path)
    result = subprocess.run(
        [exe, "use", site_name],
        cwd=str(bench_path),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return {"success": True}
    return {"success": False, "error": result.stderr or result.stdout}


def migrate_site_process(bench_path: Path, site_name: str) -> subprocess.Popen:
    exe = bench_exe(bench_path)
    return subprocess.Popen(
        [exe, "--site", site_name, "migrate"],
        cwd=str(bench_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def install_app_process(bench_path: Path, site_name: str, app_name: str) -> subprocess.Popen:
    exe = bench_exe(bench_path)
    return subprocess.Popen(
        [exe, "--site", site_name, "install-app", app_name],
        cwd=str(bench_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def backup_site_process(
    bench_path: Path, site_name: str, with_files: bool = False
) -> subprocess.Popen:
    exe = bench_exe(bench_path)
    cmd = [exe, "--site", site_name, "backup"]
    if with_files:
        cmd.append("--with-files")
    return subprocess.Popen(
        cmd,
        cwd=str(bench_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def restore_site_process(
    bench_path: Path,
    site_name: str,
    sql_file: str,
    with_public_files: str | None = None,
    with_private_files: str | None = None,
) -> subprocess.Popen:
    exe = bench_exe(bench_path)
    cmd = [exe, "--site", site_name, "restore", sql_file]
    if with_public_files:
        cmd += ["--with-public-files", with_public_files]
    if with_private_files:
        cmd += ["--with-private-files", with_private_files]
    return subprocess.Popen(
        cmd,
        cwd=str(bench_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )


def _validate_site_name(site_name: str) -> str:
    name = site_name.strip().lower()
    name = re.sub(r"[^a-z0-9\-.]", "", name)
    if not name:
        raise ValueError(f"Invalid site name: {site_name!r}")
    return name


def is_in_hosts(site_name: str) -> bool:
    try:
        for line in Path("/etc/hosts").read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("127.0.0.1", "::1") and site_name in parts[1:]:
                return True
        return False
    except Exception:
        return False


def add_to_hosts(site_name: str) -> dict:
    try:
        site_name = _validate_site_name(site_name)
        if is_in_hosts(site_name):
            return {"success": True, "already_exists": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

    hosts_entry = f"\n127.0.0.1\t{site_name}\n::1\t{site_name}\n"
    result = subprocess.run(
        ["sudo", "-n", "tee", "-a", "/etc/hosts"],
        input=hosts_entry,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return {"success": True}
    quoted = shlex.quote(site_name)
    sudo_cmd = f"printf '\\n127.0.0.1\\t{quoted}\\n::1\\t{quoted}\\n' | sudo tee -a /etc/hosts > /dev/null"
    return {
        "success": False,
        "error": "Add to hosts requires superuser access. Run the command below in a terminal.",
        "sudo_command": sudo_cmd,
    }


def remove_from_hosts(site_name: str) -> dict:
    try:
        site_name = _validate_site_name(site_name)
        if not is_in_hosts(site_name):
            return {"success": True, "not_found": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

    pattern = re.escape(site_name)
    sed_pattern = f"/^(127\\.0\\.0\\.1|::1)[[:space:]]+{pattern}([[:space:]]|$)/d"
    if platform.system() == "Darwin":
        cmd = ["sudo", "-n", "sed", "-i", "", "-E", sed_pattern, "/etc/hosts"]
    else:
        cmd = ["sudo", "-n", "sed", "-i", "-E", sed_pattern, "/etc/hosts"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return {"success": True}
    return {"success": False, "error": result.stderr.strip() or "sed failed"}


def clear_default_site(bench_path: Path) -> dict:
    currentsite = bench_path / "sites" / "currentsite"
    try:
        if currentsite.exists():
            currentsite.unlink()
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_site_backups(bench_path: Path, site_name: str) -> list[dict]:
    """Return list of backup files sorted newest first."""
    backup_dir = bench_path / "sites" / site_name / "private" / "backups"
    if not backup_dir.exists():
        return []
    files = sorted(backup_dir.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        if f.is_file():
            stat = f.stat()
            result.append(
                {
                    "filename": f.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
    return result
