"""Geração de jogos: aleatório puro ou ponderado pela frequência histórica."""

from __future__ import annotations

import random

from . import analysis
from .modalidades import Modalidade

ESTRATEGIAS = ("aleatorio", "frequencia")
MAX_TENTATIVAS_SEM_REPETIR = 200


def gerar_jogo(
    modalidade: Modalidade,
    estrategia: str = "aleatorio",
    n_jogos: int = 1,
    evitar_repetidos: bool = True,
) -> list[list[int]]:
    if estrategia not in ESTRATEGIAS:
        raise ValueError(f"Estratégia inválida: {estrategia!r}. Opções: {ESTRATEGIAS}")
    if n_jogos < 1:
        raise ValueError("n_jogos deve ser >= 1")

    sortear_um = _construir_sorteador(modalidade, estrategia)

    jogos: list[list[int]] = []
    vistos: set[tuple[int, ...]] = set()
    tentativas = 0
    while len(jogos) < n_jogos:
        jogo = sortear_um()
        chave = tuple(jogo)
        if evitar_repetidos and chave in vistos:
            tentativas += 1
            if tentativas > MAX_TENTATIVAS_SEM_REPETIR:
                raise RuntimeError(
                    "Não foi possível gerar jogos suficientes sem repetição; "
                    "reduza n_jogos ou desative evitar_repetidos."
                )
            continue
        vistos.add(chave)
        jogos.append(jogo)
        tentativas = 0

    return jogos


def _construir_sorteador(modalidade: Modalidade, estrategia: str):
    populacao = list(range(modalidade.numero_min, modalidade.numero_max + 1))
    k = modalidade.qtd_numeros_por_jogo

    if estrategia == "aleatorio":
        def sortear() -> list[int]:
            return sorted(random.sample(populacao, k))
        return sortear

    estatisticas = analysis.calcular_estatisticas(modalidade)
    pesos = [estatisticas.frequencia.get(n, 0) + 1 for n in populacao]  # +1 evita peso zero

    def sortear() -> list[int]:
        return sorted(_amostra_ponderada_sem_reposicao(populacao, pesos, k))

    return sortear


def _amostra_ponderada_sem_reposicao(populacao: list[int], pesos: list[int], k: int) -> list[int]:
    pool = list(zip(populacao, pesos))
    escolhidos: list[int] = []
    for _ in range(k):
        total = sum(peso for _, peso in pool)
        alvo = random.uniform(0, total)
        acumulado = 0.0
        for indice, (numero, peso) in enumerate(pool):
            acumulado += peso
            if acumulado >= alvo:
                escolhidos.append(numero)
                pool.pop(indice)
                break
    return escolhidos
