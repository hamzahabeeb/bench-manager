import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bench_root: str = str(Path.home())
    host: str = "0.0.0.0"
    port: int = 8500
    secret_key: str = "change-me-in-production"
    # Override if 'bench' is not on PATH (e.g. /home/frappe/.local/bin/bench)
    bench_cmd: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "BENCH_MANAGER_"


settings = Settings()
