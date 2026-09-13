"""Camada de persistência local (SQLite) para os resultados das loterias."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path

from .api import PremioFaixa, Resultado


def _resolver_db_path() -> Path:
    """Em modo normal (`streamlit run app.py`), usa `data/resultados.db` dentro do
    projeto. Empacotado como executável (PyInstaller), `__file__` aponta para uma
    pasta temporária que é apagada ao fechar o app — nesse caso o cache é salvo
    numa pasta persistente do usuário, para não perder os dados sincronizados
    a cada execução."""
    if getattr(sys, "frozen", False):
        base = Path(os.getenv("APPDATA") or Path.home()) / "LoteriasDaCaixa"
        return base / "resultados.db"
    return Path(__file__).resolve().parent.parent / "data" / "resultados.db"


DB_PATH = _resolver_db_path()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS resultados (
    modalidade TEXT NOT NULL,
    concurso INTEGER NOT NULL,
    data TEXT NOT NULL,
    dezenas TEXT NOT NULL,
    acumulado INTEGER NOT NULL,
    valor_acumulado_proximo REAL NOT NULL DEFAULT 0,
    data_proximo_concurso TEXT NOT NULL DEFAULT '',
    premios TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (modalidade, concurso)
);
"""

# Colunas adicionadas após a versão inicial do schema; migradas em bancos já existentes.
_COLUNAS_EXTRAS = {
    "valor_acumulado_proximo": "REAL NOT NULL DEFAULT 0",
    "data_proximo_concurso": "TEXT NOT NULL DEFAULT ''",
    "premios": "TEXT NOT NULL DEFAULT '[]'",
}


def _conectar() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(DB_PATH)
    conexao.execute(_SCHEMA)
    _migrar(conexao)
    return conexao


def _migrar(conexao: sqlite3.Connection) -> None:
    colunas_existentes = {linha[1] for linha in conexao.execute("PRAGMA table_info(resultados)")}
    for nome, definicao in _COLUNAS_EXTRAS.items():
        if nome not in colunas_existentes:
            conexao.execute(f"ALTER TABLE resultados ADD COLUMN {nome} {definicao}")


def salvar_resultado(resultado: Resultado) -> None:
    with _conectar() as conexao:
        conexao.execute(
            """
            INSERT INTO resultados (
                modalidade, concurso, data, dezenas, acumulado,
                valor_acumulado_proximo, data_proximo_concurso, premios
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(modalidade, concurso) DO UPDATE SET
                data = excluded.data,
                dezenas = excluded.dezenas,
                acumulado = excluded.acumulado,
                valor_acumulado_proximo = excluded.valor_acumulado_proximo,
                data_proximo_concurso = excluded.data_proximo_concurso,
                premios = excluded.premios
            """,
            (
                resultado.modalidade,
                resultado.concurso,
                resultado.data,
                json.dumps(resultado.dezenas),
                int(resultado.acumulado),
                resultado.valor_acumulado_proximo,
                resultado.data_proximo_concurso,
                json.dumps([asdict(p) for p in resultado.premios]),
            ),
        )


def ultimo_concurso_salvo(modalidade_chave: str) -> int | None:
    with _conectar() as conexao:
        linha = conexao.execute(
            "SELECT MAX(concurso) FROM resultados WHERE modalidade = ?",
            (modalidade_chave,),
        ).fetchone()
    return linha[0] if linha and linha[0] is not None else None


def concursos_salvos(modalidade_chave: str) -> set[int]:
    with _conectar() as conexao:
        linhas = conexao.execute(
            "SELECT concurso FROM resultados WHERE modalidade = ?",
            (modalidade_chave,),
        ).fetchall()
    return {linha[0] for linha in linhas}


def primeiro_concurso_salvo(modalidade_chave: str) -> int | None:
    with _conectar() as conexao:
        linha = conexao.execute(
            "SELECT MIN(concurso) FROM resultados WHERE modalidade = ?",
            (modalidade_chave,),
        ).fetchone()
    return linha[0] if linha and linha[0] is not None else None


def apagar_modalidade(modalidade_chave: str) -> None:
    with _conectar() as conexao:
        conexao.execute("DELETE FROM resultados WHERE modalidade = ?", (modalidade_chave,))


def carregar_resultado(modalidade_chave: str, concurso: int) -> Resultado | None:
    with _conectar() as conexao:
        linha = conexao.execute(
            "SELECT modalidade, concurso, data, dezenas, acumulado, "
            "valor_acumulado_proximo, data_proximo_concurso, premios FROM resultados "
            "WHERE modalidade = ? AND concurso = ?",
            (modalidade_chave, concurso),
        ).fetchone()
    if linha is None:
        return None
    return _linha_para_resultado(linha)


def carregar_historico(modalidade_chave: str) -> list[Resultado]:
    with _conectar() as conexao:
        linhas = conexao.execute(
            "SELECT modalidade, concurso, data, dezenas, acumulado, "
            "valor_acumulado_proximo, data_proximo_concurso, premios FROM resultados "
            "WHERE modalidade = ? ORDER BY concurso ASC",
            (modalidade_chave,),
        ).fetchall()
    return [_linha_para_resultado(linha) for linha in linhas]


def _linha_para_resultado(linha) -> Resultado:
    (
        modalidade,
        concurso,
        data,
        dezenas_json,
        acumulado,
        valor_acumulado_proximo,
        data_proximo_concurso,
        premios_json,
    ) = linha
    return Resultado(
        modalidade=modalidade,
        concurso=concurso,
        data=data,
        dezenas=json.loads(dezenas_json),
        acumulado=bool(acumulado),
        valor_acumulado_proximo=valor_acumulado_proximo,
        data_proximo_concurso=data_proximo_concurso,
        premios=[PremioFaixa(**item) for item in json.loads(premios_json)],
    )
