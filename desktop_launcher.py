"""Ponto de entrada do executável desktop (PyInstaller).

Sobe o servidor Streamlit num **subprocesso** próprio e abre uma janela nativa
(via `pywebview`, usando o WebView2/Edge Chromium do Windows) apontando pra
ele — do ponto de vista de quem clica no .exe, é um app desktop de verdade:
uma janela só, sem terminal visível e sem aba de navegador separada.

Por que um subprocesso e não só uma thread? O próprio bootstrap do Streamlit
registra handlers de sinal (SIGTERM) ao subir, e isso só é permitido na
thread principal do processo — e a thread principal já está ocupada com o
loop de eventos da janela nativa (pywebview também exige rodar na principal).
Duas threads principais não cabem no mesmo processo, então o servidor sobe
num processo próprio; a janela some assim que a janela é fechada.

Se o WebView2 não estiver disponível na máquina (raro — vem pré-instalado
desde o Windows 10 21H2/Windows 11), cai de volta para abrir no navegador
padrão em vez de travar o app.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# Empacotado com `--windowed`, o Windows roda o processo sem console e deixa
# sys.stdout/stderr como None — bibliotecas que tentam escrever neles (o
# próprio Streamlit/click inclusive) derrubariam o app com um AttributeError.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

os.environ["LOTERIAS_DESKTOP"] = "1"

_FLAG_SERVIDOR = "--rodar-servidor-streamlit"


def _caminho_app() -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / "app.py")


def _porta_livre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _porta_pronta(porta: int, tentativas: int = 120) -> bool:
    for _ in range(tentativas):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", porta))
                return True
            except OSError:
                time.sleep(0.5)
    return False


def _matar_filho_se_pai_morrer(processo: subprocess.Popen) -> None:
    """Amarra o subprocesso do Streamlit a um Job Object do Windows com
    `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, garantindo que ele morre junto se
    este processo (o launcher) for encerrado de qualquer jeito — inclusive à
    força (crash, Gerenciador de Tarefas, fim de sessão). Sem isso, matar só
    o launcher deixava o servidor Streamlit órfão, rodando pra sempre: o
    `finally: processo.terminate()` em `main()` só roda numa saída graciosa,
    e não ajuda quando o próprio processo é morto de fora."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        JobObjectExtendedLimitInformation = 9

        class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32),
            ]

        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(nome, ctypes.c_uint64) for nome in (
                "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
            )]

        class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        kernel32 = ctypes.windll.kernel32
        job = kernel32.CreateJobObjectW(None, None)
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        kernel32.SetInformationJobObject(
            job, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info)
        )
        kernel32.AssignProcessToJobObject(job, int(processo._handle))
    except Exception:
        pass  # melhor esforço — na pior das hipóteses, cai no comportamento anterior


def _rodar_servidor_streamlit(porta: int) -> None:
    """Processo filho: roda o Streamlit de verdade. Isso é chamado como a
    função principal de um processo próprio (veja o módulo acima), então
    o registro de handler de sinal do bootstrap do Streamlit funciona
    normalmente."""
    from streamlit.web import cli as stcli

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


def main() -> None:
    if _FLAG_SERVIDOR in sys.argv:
        porta = int(sys.argv[sys.argv.index(_FLAG_SERVIDOR) + 1])
        _rodar_servidor_streamlit(porta)
        return

    porta = _porta_livre()
    comando = (
        [sys.executable]
        if getattr(sys, "frozen", False)
        else [sys.executable, str(Path(__file__).resolve())]
    )
    processo = subprocess.Popen(comando + [_FLAG_SERVIDOR, str(porta)])
    _matar_filho_se_pai_morrer(processo)

    try:
        if not _porta_pronta(porta):
            raise RuntimeError("O servidor local do Streamlit não respondeu a tempo.")

        url = f"http://localhost:{porta}"
        try:
            import webview

            webview.create_window(
                "Loterias da Caixa",
                url,
                width=1400,
                height=880,
                min_size=(960, 640),
            )
            webview.start(gui="edgechromium")
        except Exception:
            # Sem WebView2 disponível (ou qualquer outra falha ao criar a
            # janela nativa): melhor abrir no navegador padrão do que travar.
            webbrowser.open(url)
            processo.wait()
    finally:
        processo.terminate()


if __name__ == "__main__":
    main()
