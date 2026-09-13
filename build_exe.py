"""Empacota o app como um .exe standalone para Windows (via PyInstaller).

Uso:
    pip install pyinstaller
    python build_exe.py

Gera dist/LoteriasDaCaixa.exe. Veja o README (seção "Executável para Windows")
para detalhes sobre por que isso é necessário além de `pip install -r requirements.txt`.
"""

import PyInstaller.__main__

PyInstaller.__main__.run([
    "--name", "LoteriasDaCaixa",
    "--onefile",
    "--icon", "assets/icon.ico",
    "--add-data", "app.py;.",
    "--add-data", "loteria;loteria",
    "--collect-all", "streamlit",
    "--collect-all", "pandas",
    "--collect-all", "pyarrow",
    "--copy-metadata", "streamlit",
    "--copy-metadata", "pandas",
    "--noconfirm",
    "desktop_launcher.py",
])
