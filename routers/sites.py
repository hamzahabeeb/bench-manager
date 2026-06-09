from pathlib import Path

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse as FastAPIFileResponse

from config import settings
from core.bench import get_bench_info, is_bench_dir
from core.logs import register_job
from core.sites import (
    backup_site_process,
    create_site_process,
    drop_site,
    install_app_process,
    list_site_backups,
    list_sites,
    migrate_site_process,
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
        bench_path, site_name, admin_password,
        db_name=db_name or None,
        db_root_password=db_root_password or None,
    )
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.delete("/{bench_name}/sites/{site_name}")
async def site_drop(bench_name: str, site_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    result = drop_site(bench_path, site_name)
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
