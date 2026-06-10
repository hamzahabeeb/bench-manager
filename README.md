# Bench Manager

A lightweight web UI for managing multiple [Frappe](https://frappeframework.com) bench instances on a single server.

![Dashboard]
<img width="1456" height="825" alt="image" src="https://github.com/user-attachments/assets/b3857880-867f-4e89-b92c-7588e01647ff" />


## Features

- **Dashboard** — view all benches in one place with live status
- **Start / Stop** benches with one click
- **Live logs** — tail `web`, `worker`, `scheduler`, and `error` logs in real time
- **Site management** — create, drop, migrate, install apps, and back up sites
- **Backup download** — trigger a backup and download the files directly from the browser
- **Create / Delete** benches (runs `bench init` with live output)
- Auto-detects the `bench` executable (searches virtualenv, PATH, `~/.local/bin`, macOS user installs)

## Requirements

- Python 3.10+
- One or more Frappe bench installations

> Node.js is **not required** to run the app — the frontend is pre-built and included.
> Only needed if you want to modify the frontend source.

## Quick start

```bash
git clone https://github.com/your-username/bench-manager
cd bench-manager

# edit the config (add the folder in which all your benches are present in line with BENCH_MANAGER_BENCH_ROOT)
nano .env

# Start the server (creates venv and installs deps automatically)
./run.sh
```

Open **http://localhost:8500** in your browser.

## Frontend development

The production build is served directly by the FastAPI server. For live-reload development:

```bash
# Terminal 1 — backend
./run.sh

# Terminal 2 — frontend dev server (hot reload at :8080)
cd frontend
npm install
npm run dev
```

Open **http://localhost:8080** — API calls are proxied to the backend.

To rebuild the frontend for production:

```bash
cd frontend && npm run build
```

## Configuration

All settings are read from environment variables (or a `.env` file in the project root):

| Variable | Default | Description |
|---|---|---|
| `BENCH_MANAGER_BENCH_ROOT` | `$HOME` | Directory scanned for bench instances |
| `BENCH_MANAGER_HOST` | `0.0.0.0` | Host to bind the server to |
| `BENCH_MANAGER_PORT` | `8500` | Port to listen on |
| `BENCH_MANAGER_SECRET_KEY` | `change-me` | Secret key (change in production) |
| `BENCH_MANAGER_BENCH_CMD` | _(auto-detect)_ | Full path to the `bench` executable |

### Bench discovery

A directory is recognised as a Frappe bench if it contains all three of:
- `Procfile`
- `apps/`
- `sites/`

By default every directory under `$HOME` is scanned. Set `BENCH_MANAGER_BENCH_ROOT` to a different path if your benches live elsewhere (e.g. `/home/frappe` on a production server).

### `bench` executable

The app searches for `bench` in this order:
1. `BENCH_MANAGER_BENCH_CMD` env var (explicit override)
2. `<bench_dir>/env/bin/bench` (bench virtualenv)
3. `bench` on `$PATH`
4. `~/.local/bin/bench` (pip user install — common on Linux)
5. `/opt/homebrew/bin/bench` (Homebrew — macOS)
6. `~/Library/Python/X.Y/bin/bench` (macOS pip install, tries Python 3.9–3.13)

## How it works

```
Browser → FastAPI (:8500) → Frappe bench processes
                ↓
         frontend/dist/   ← built Vue 3 + Frappe UI SPA
```

- **Backend**: FastAPI + psutil for process management; Server-Sent Events for live log/job streaming
- **Frontend**: Vue 3 + [Frappe UI](https://github.com/frappe/frappe-ui) component library + Tailwind CSS
- **Process manager**: [honcho](https://honcho.readthedocs.io) (auto-installed per bench if missing)

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, uvicorn, psutil, sse-starlette |
| Frontend | Vue 3, Frappe UI, Tailwind CSS v3, Vite |
| Process management | honcho (Procfile runner) |

## License

MIT
