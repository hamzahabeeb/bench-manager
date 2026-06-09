from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import settings
from routers import benches, logs, sites

app = FastAPI(title="Bench Manager", version="1.0.0")

app.include_router(benches.router)
app.include_router(sites.router)
app.include_router(logs.router)


@app.get("/health")
async def health():
    return {"status": "ok", "bench_root": settings.bench_root}


# Serve the Vue frontend (production build)
_DIST = Path(__file__).parent / "frontend" / "dist"

if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        candidate = _DIST / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_DIST / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    async def dev_root():
        return JSONResponse(
            {"message": "Bench Manager API running. Start the frontend dev server: cd frontend && npm run dev"},
            status_code=200,
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
