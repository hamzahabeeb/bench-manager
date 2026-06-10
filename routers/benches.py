from pathlib import Path

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse

from config import settings
from core.bench import (
    BenchInfo,
    _get_port,
    bench_exec_process,
    build_bench_process,
    create_bench_process,
    delete_bench,
    discover_benches,
    get_bench_info,
    get_bench_status,
    install_honcho,
    is_bench_dir,
    start_bench,
    stop_bench,
)
from core.logs import register_job
from core.sites import list_sites

router = APIRouter(prefix="/api/benches", tags=["benches"])


@router.get("")
async def bench_list():
    benches = discover_benches()
    return {"benches": [b.to_dict() for b in benches]}


@router.get("/{bench_name}")
async def bench_detail(bench_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")
    bench = get_bench_info(bench_path)
    sites = list_sites(bench_path)
    return {"bench": bench.to_dict(), "sites": [s.to_dict() for s in sites]}


@router.get("/{bench_name}/status")
async def bench_status(bench_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    status = get_bench_status(bench_name)
    port = _get_port(bench_path) if is_bench_dir(bench_path) else 0
    return {"status": status, "port": port}


@router.post("/{bench_name}/start")
async def bench_start(bench_name: str):
    bench_path = Path(settings.bench_root) / bench_name
    result = start_bench(bench_name)
    status = "running" if result["success"] else "stopped"
    message = result.get("error", "")
    return {
        "success": result["success"],
        "status": status,
        "message": message,
        "missing_honcho": result.get("missing_honcho", False),
    }


@router.post("/{bench_name}/stop")
async def bench_stop(bench_name: str):
    stop_bench(bench_name)
    return {"success": True, "status": "stopped"}


@router.post("/create")
async def bench_create(
    bench_name: str = Form(...),
    frappe_branch: str = Form("version-15"),
):
    try:
        proc = create_bench_process(bench_name, frappe_branch)
        job_id = register_job(proc)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"job_id": job_id}


@router.delete("/{bench_name}")
async def bench_delete(bench_name: str):
    result = delete_bench(bench_name)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Delete failed"))
    return {"success": True}


@router.post("/{bench_name}/exec")
async def bench_exec(bench_name: str, command: str = Form(...)):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")
    proc = bench_exec_process(bench_name, command)
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.post("/{bench_name}/build")
async def bench_build(
    bench_name: str,
    app: str = Form(""),
    force: bool = Form(False),
):
    bench_path = Path(settings.bench_root) / bench_name
    if not is_bench_dir(bench_path):
        raise HTTPException(status_code=404, detail="Bench not found")
    proc = build_bench_process(bench_name, app=app or None, force=force)
    job_id = register_job(proc)
    return {"job_id": job_id}


@router.post("/{bench_name}/install-honcho")
async def bench_install_honcho(bench_name: str):
    result = install_honcho(bench_name)
    return {
        "success": result["success"],
        "message": result.get("error", "honcho installed successfully") if not result["success"] else "honcho installed successfully",
    }
