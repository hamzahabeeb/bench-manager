"""macOS menu bar tray app for Bench Manager."""

import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import rumps

APP_NAME = "Bench Manager"
URL = "http://localhost:8500"
SCRIPT_DIR = Path(__file__).parent


def _server_running() -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(URL + "/api/benches", timeout=2)
        return True
    except Exception:
        return False


class BenchManagerApp(rumps.App):
    def __init__(self):
        super().__init__(APP_NAME, quit_button=None)
        self._server_proc: subprocess.Popen | None = None
        self._set_icon(running=False)
        self.menu = [
            rumps.MenuItem("Open UI", callback=self.open_ui),
            None,  # separator
            rumps.MenuItem("Start Server", callback=self.start_server),
            rumps.MenuItem("Stop Server", callback=self.stop_server),
            rumps.MenuItem("Restart Server", callback=self.restart_server),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]
        # Auto-start server on launch
        threading.Thread(target=self._auto_start, daemon=True).start()

    # ------------------------------------------------------------------
    def _set_icon(self, running: bool) -> None:
        self.title = f"{'🟢' if running else '⚫'} Bench"

    def _update_menu_state(self, running: bool) -> None:
        self._set_icon(running)
        self.menu["Open UI"].set_callback(self.open_ui if running else None)
        self.menu["Start Server"].set_callback(None if running else self.start_server)
        self.menu["Stop Server"].set_callback(self.stop_server if running else None)

    # ------------------------------------------------------------------
    def _auto_start(self) -> None:
        if not _server_running():
            self._launch_server()

    def _launch_server(self) -> None:
        env = os.environ.copy()
        venv_bin = str(SCRIPT_DIR / ".venv" / "bin")
        env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")

        python = SCRIPT_DIR / ".venv" / "bin" / "python"
        if not python.exists():
            python = Path(sys.executable)

        self._server_proc = subprocess.Popen(
            [str(python), str(SCRIPT_DIR / "main.py")],
            cwd=str(SCRIPT_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Poll until ready (up to 15s)
        import time
        for _ in range(30):
            time.sleep(0.5)
            if _server_running():
                rumps.notification(APP_NAME, "", "Server started on port 8500")
                self._update_menu_state(True)
                return
        rumps.notification(APP_NAME, "Warning", "Server did not respond after 15s")

    # ------------------------------------------------------------------
    def open_ui(self, _=None) -> None:
        webbrowser.open(URL)

    def start_server(self, _=None) -> None:
        if _server_running():
            rumps.notification(APP_NAME, "", "Already running")
            return
        self.menu["Start Server"].set_callback(None)
        threading.Thread(target=self._launch_server, daemon=True).start()

    def stop_server(self, _=None) -> None:
        if self._server_proc:
            self._server_proc.terminate()
            self._server_proc = None
        self._update_menu_state(False)
        rumps.notification(APP_NAME, "", "Server stopped")

    def restart_server(self, _=None) -> None:
        self.stop_server()
        import time; time.sleep(1)
        threading.Thread(target=self._launch_server, daemon=True).start()

    def quit_app(self, _=None) -> None:
        self.stop_server()
        rumps.quit_application()


if __name__ == "__main__":
    BenchManagerApp().run()
