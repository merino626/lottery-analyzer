"""Empacota o app como um .exe desktop para Windows (via PyInstaller).

Uso:
    pip install -r requirements-desktop.txt
    python build_exe.py

Gera dist/LoteriasDaCaixa/LoteriasDaCaixa.exe — uma pasta (modo "onedir"), não
um único arquivo: isso evita a extração para uma pasta temporária a cada
execução (lenta, e o launcher precisa subir o Streamlit num subprocesso que
reexecuta o próprio .exe — com "onefile" isso significaria extrair tudo duas
vezes a cada abertura do app). Para distribuir, zipe a pasta inteira.

Veja o README (seção "Executável para Windows") para o porquê de cada peça.
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    "--name", "LoteriasDaCaixa",
    "--windowed",
    "--icon", "assets/icon.ico",
    "--add-data", "app.py;.",
    "--add-data", "loteria;loteria",
    "--collect-all", "streamlit",
    "--collect-all", "pandas",
    "--collect-all", "pyarrow",
    "--collect-all", "webview",
    "--copy-metadata", "streamlit",
    "--copy-metadata", "pandas",
    "--noconfirm",
    "desktop_launcher.py",
])
