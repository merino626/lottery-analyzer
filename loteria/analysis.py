"""Estatísticas sobre o histórico de resultados de uma modalidade."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from . import storage
from .api import Resultado
from .modalidades import Modalidade


@dataclass(frozen=True)
class Estatisticas:
    modalidade: str
    total_concursos: int
    frequencia: dict[int, int]          # dezena -> quantas vezes saiu
    atraso: dict[int, int]                # dezena -> concursos desde a última vez que saiu
    media_pares: float
    media_impares: float
    media_soma: float


def calcular_estatisticas(modalidade: Modalidade) -> Estatisticas:
    historico = storage.carregar_historico(modalidade.chave)
    if not historico:
        raise ValueError(
            f"Sem histórico local para {modalidade.nome}. Rode a sincronização primeiro."
        )

    frequencia = Counter()
    for resultado in historico:
        frequencia.update(resultado.dezenas)

    todas_dezenas = range(modalidade.numero_min, modalidade.numero_max + 1)
    for dezena in todas_dezenas:
        frequencia.setdefault(dezena, 0)

    atraso = _calcular_atraso(historico, todas_dezenas)

    pares, impares, somas = [], [], []
    for resultado in historico:
        n_pares = sum(1 for d in resultado.dezenas if d % 2 == 0)
        pares.append(n_pares)
        impares.append(len(resultado.dezenas) - n_pares)
        somas.append(sum(resultado.dezenas))

    return Estatisticas(
        modalidade=modalidade.chave,
        total_concursos=len(historico),
        frequencia=dict(sorted(frequencia.items())),
        atraso=atraso,
        media_pares=sum(pares) / len(pares),
        media_impares=sum(impares) / len(impares),
        media_soma=sum(somas) / len(somas),
    )


def _calcular_atraso(historico: list[Resultado], todas_dezenas: range) -> dict[int, int]:
    ultimo_indice: dict[int, int] = {}
    for indice, resultado in enumerate(historico):
        for dezena in resultado.dezenas:
            ultimo_indice[dezena] = indice

    total = len(historico)
    atraso = {}
    for dezena in todas_dezenas:
        if dezena in ultimo_indice:
            atraso[dezena] = total - 1 - ultimo_indice[dezena]
        else:
            atraso[dezena] = total
    return atraso


def mais_sorteadas(estatisticas: Estatisticas, n: int = 10) -> list[tuple[int, int]]:
    return sorted(estatisticas.frequencia.items(), key=lambda item: item[1], reverse=True)[:n]


def menos_sorteadas(estatisticas: Estatisticas, n: int = 10) -> list[tuple[int, int]]:
    return sorted(estatisticas.frequencia.items(), key=lambda item: item[1])[:n]


def mais_atrasadas(estatisticas: Estatisticas, n: int = 10) -> list[tuple[int, int]]:
    return sorted(estatisticas.atraso.items(), key=lambda item: item[1], reverse=True)[:n]
