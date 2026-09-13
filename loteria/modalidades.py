"""Configuração das modalidades de loteria da Caixa suportadas pelo sistema."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Modalidade:
    chave: str          # identificador interno, usado como nome de tabela/arquivo
    nome: str            # nome de exibição
    slug_api: str         # slug usado na API da Caixa
    qtd_numeros_por_jogo: int   # quantas dezenas o apostador escolhe
    numero_min: int
    numero_max: int


MEGA_SENA = Modalidade("mega_sena", "Mega-Sena", "megasena", 6, 1, 60)
LOTOFACIL = Modalidade("lotofacil", "Lotofácil", "lotofacil", 15, 1, 25)
QUINA = Modalidade("quina", "Quina", "quina", 5, 1, 80)
LOTOMANIA = Modalidade("lotomania", "Lotomania", "lotomania", 50, 0, 99)
DUPLA_SENA = Modalidade("dupla_sena", "Dupla-Sena", "duplasena", 6, 1, 50)
TIMEMANIA = Modalidade("timemania", "Timemania", "timemania", 10, 1, 80)
MAIS_MILIONARIA = Modalidade("mais_milionaria", "+Milionária", "maismilionaria", 6, 1, 50)
DIA_DE_SORTE = Modalidade("dia_de_sorte", "Dia de Sorte", "diadesorte", 7, 1, 31)

TODAS = [
    MEGA_SENA,
    LOTOFACIL,
    QUINA,
    LOTOMANIA,
    DUPLA_SENA,
    TIMEMANIA,
    MAIS_MILIONARIA,
    DIA_DE_SORTE,
]

POR_CHAVE = {m.chave: m for m in TODAS}


def obter(chave: str) -> Modalidade:
    try:
        return POR_CHAVE[chave]
    except KeyError:
        raise ValueError(f"Modalidade desconhecida: {chave!r}. Opções: {list(POR_CHAVE)}")
