from pathlib import Path

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from config import settings
from core.logs import stream_job, stream_log

router = APIRouter(tags=["logs"])


@router.get("/api/benches/{bench_name}/logs/{log_type}/stream")
async def log_stream(bench_name: str, log_type: str = "web"):
    bench_path = Path(settings.bench_root) / bench_name

    async def generator():
        async for line in stream_log(bench_path, log_type):
            yield {"data": line.rstrip("\n")}

    return EventSourceResponse(generator())


@router.get("/api/jobs/{job_id}/stream")
async def job_stream(job_id: str):
    async def generator():
        async for line in stream_job(job_id):
            yield {"data": line.rstrip("\n")}

    return EventSourceResponse(generator())
