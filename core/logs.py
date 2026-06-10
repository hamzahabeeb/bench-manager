import asyncio
import subprocess
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

LOG_FILES = {
    "web": "logs/web.log",
    "worker": "logs/worker.log",
    "scheduler": "logs/scheduler.log",
    "error": "logs/error.log",
    "bench": "logs/bench.log",
}

# Job registry: job_id -> subprocess.Popen
_JOBS: dict[str, subprocess.Popen] = {}


def register_job(proc: subprocess.Popen) -> str:
    job_id = str(uuid.uuid4())[:8]
    _JOBS[job_id] = proc
    return job_id


def get_job(job_id: str) -> subprocess.Popen | None:
    return _JOBS.get(job_id)


def cleanup_job(job_id: str) -> None:
    _JOBS.pop(job_id, None)


async def stream_log(bench_path: Path, log_type: str = "web") -> AsyncGenerator[str, None]:
    rel = LOG_FILES.get(log_type)
    if not rel:
        yield f"Unknown log type: {log_type}\n"
        return

    log_file = bench_path / rel
    if not log_file.exists():
        # Poll silently; EventSource will reconnect when connection closes
        for _ in range(30):
            await asyncio.sleep(2)
            if log_file.exists():
                break
        else:
            return

    proc = await asyncio.create_subprocess_exec(
        "tail",
        "-n",
        "200",
        "-f",
        str(log_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        while True:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=30.0)  # type: ignore[union-attr]
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if not line:
                break
            yield line.decode("utf-8", errors="replace")
    finally:
        proc.terminate()


async def stream_job(job_id: str) -> AsyncGenerator[str, None]:
    proc = get_job(job_id)
    if proc is None:
        yield f"Job {job_id} not found.\n"
        return

    loop = asyncio.get_event_loop()
    try:
        while True:
            line = await loop.run_in_executor(None, proc.stdout.readline)  # type: ignore[union-attr]
            if not line:
                break
            yield line
        rc = proc.wait()
        yield f"\n--- Process exited with code {rc} ---\n"
    finally:
        cleanup_job(job_id)
