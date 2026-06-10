from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse as FastAPIFileResponse

from config import settings
from core.bench import is_bench_dir
from core.logs import register_job
from core.sites import (
    add_to_hosts,
    backup_site_process,
    clear_default_site,
    create_site_process,
    drop_site,
    install_app_process,
    is_in_hosts,
    list_site_backups,
    list_sites,
    migrate_site_process,
    remove_from_hosts,
    restore_site_process,
    use_site,
)

router = APIRouter(prefix="/api/benches", tags=["sites"])


@router.get("/{bench_name}/sites")
async def site_list(bench_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")
    sites = list_sites(bench_path)
    return {"sites": [s.to_dict() for s in sites]}


@router.post("/{bench_name}/sites")
async def site_create(
    bench_name: str,
    site_name: str = Form(...),
    admin_password: str = Form(...),
    db_name: str = Form(""),
    db_root_password: str = Form(""),
):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")

    proc = create_site_process(
        bench_path,
        site_name,
        admin_password,
        db_name=db_name or None,
        db_root_password=db_root_password or None,
    )
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.delete("/{bench_name}/sites/{site_name}")
async def site_drop(bench_name: str, site_name: str, root_password: str = ""):
    bench_path = Path(settings.bench_root) / bench_name
    result = drop_site(bench_path, site_name, root_password=root_password)
    return {"success": result["success"], "error": result.get("error", "")}


@router.post("/{bench_name}/sites/{site_name}/use")
async def site_use(bench_name: str, site_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")
    result = use_site(bench_path, site_name)
    return {"success": result["success"], "error": result.get("error", "")}


@router.post("/{bench_name}/sites/{site_name}/migrate")
async def site_migrate(bench_name: str, site_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    proc = migrate_site_process(bench_path, site_name)
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.post("/{bench_name}/sites/{site_name}/install-app")
async def site_install_app(
    bench_name: str,
    site_name: str,
    app_name: str = Form(...),
):
    bench_path = Path(settings.bench_root) / bench_name
    proc = install_app_process(bench_path, site_name, app_name)
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.post("/{bench_name}/sites/{site_name}/backup")
async def site_backup(bench_name: str, site_name: str, with_files: bool = False):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")
    proc = backup_site_process(bench_path, site_name, with_files=with_files)
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.get("/{bench_name}/sites/{site_name}/backups")
async def site_backups_list(bench_name: str, site_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    backups = list_site_backups(bench_path, site_name)
    return {"backups": backups}


@router.post("/{bench_name}/sites/{site_name}/restore")
async def site_restore(
    bench_name: str,
    site_name: str,
    sql_file: UploadFile = File(...),
    public_file: UploadFile | None = File(default=None),
    private_file: UploadFile | None = File(default=None),
):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")

    backup_dir = bench_path / "sites" / site_name / "private" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(upload: UploadFile) -> str:
        dest = backup_dir / (upload.filename or "upload.sql")
        with open(dest, "wb") as fh:
            while chunk := await upload.read(1024 * 1024):
                fh.write(chunk)
        return str(dest)

    sql_path = await save_upload(sql_file)
    public_path = await save_upload(public_file) if public_file and public_file.filename else None
    private_path = (
        await save_upload(private_file) if private_file and private_file.filename else None
    )

    proc = restore_site_process(bench_path, site_name, sql_path, public_path, private_path)
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.get("/{bench_name}/sites/{site_name}/hosts-status")
async def site_hosts_status(bench_name: str, site_name: str):  # noqa: ARG001
    _ = bench_name
    return {"in_hosts": is_in_hosts(site_name)}


@router.post("/{bench_name}/sites/{site_name}/add-host")
async def site_add_host(bench_name: str, site_name: str):  # noqa: ARG001
    _ = bench_name
    result = add_to_hosts(site_name)
    return {
        "success": result["success"],
        "error": result.get("error", ""),
        "sudo_command": result.get("sudo_command", ""),
    }


@router.delete("/{bench_name}/sites/{site_name}/remove-host")
async def site_remove_host(bench_name: str, site_name: str):  # noqa: ARG001
    _ = bench_name
    result = remove_from_hosts(site_name)
    return {"success": result["success"], "error": result.get("error", "")}


@router.post("/{bench_name}/clear-default-site")
async def bench_clear_default_site(bench_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")
    result = clear_default_site(bench_path)
    return {"success": result["success"], "error": result.get("error", "")}


@router.get("/{bench_name}/sites/{site_name}/backups/{filename}")
async def site_backup_download(bench_name: str, site_name: str, filename: str):
    # Security: only allow files in the backup dir, no path traversal
    bench_path = Path(settings.bench_root) / bench_name
    backup_file = bench_path / "sites" / site_name / "private" / "backups" / filename
    if ".." in filename or not backup_file.exists() or not backup_file.is_file():
        raise HTTPException(status_code=404, detail="Backup file not found")
    return FastAPIFileResponse(
        str(backup_file),
        filename=filename,
        media_type="application/octet-stream",
    )
