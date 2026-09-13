"""Ponto de entrada do executável desktop (PyInstaller).

Sobe o servidor Streamlit localmente numa porta livre, espera ele responder e
abre o navegador padrão automaticamente — do ponto de vista de quem clica no
.exe, é um app desktop comum, mesmo sendo uma aplicação web por baixo.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from streamlit.web import cli as stcli


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _caminho_app() -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / "app.py")


def _esperar_e_abrir_navegador(porta: int) -> None:
    url = f"http://localhost:{porta}"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        for _ in range(120):  # até ~60s
            try:
                s.connect(("127.0.0.1", porta))
                break
            except OSError:
                time.sleep(0.5)
    webbrowser.open(url)


def main() -> None:
    porta = _porta_livre()
    threading.Thread(target=_esperar_e_abrir_navegador, args=(porta,), daemon=True).start()

    sys.argv = [
        "streamlit",
        "run",
        _caminho_app(),
        "--server.port",
        str(porta),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
        "--global.developmentMode",
        "false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
