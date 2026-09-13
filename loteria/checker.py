"""Conferência de jogos do usuário contra resultados oficiais, com premiação."""

from __future__ import annotations

from dataclasses import dataclass

from . import storage
from .api import PremioFaixa, Resultado, buscar_resultado
from .modalidades import Modalidade


@dataclass(frozen=True)
class ResultadoConferencia:
    concurso: int
    data: str
    dezenas_sorteadas: list[int]
    acertos: list[int]
    premio: PremioFaixa | None   # faixa de premiação correspondente à quantidade de acertos, se houver

    @property
    def total_acertos(self) -> int:
        return len(self.acertos)

    @property
    def valor_ganho(self) -> float:
        return self.premio.valor if self.premio else 0.0


@dataclass(frozen=True)
class Ganho:
    concurso: int
    data: str
    acertos: int
    descricao_faixa: str
    valor: float


def _validar_jogo(modalidade: Modalidade, jogo: list[int]) -> None:
    fora_da_faixa = [n for n in jogo if not (modalidade.numero_min <= n <= modalidade.numero_max)]
    if fora_da_faixa:
        raise ValueError(
            f"Números fora da faixa válida ({modalidade.numero_min}-{modalidade.numero_max}): {fora_da_faixa}"
        )
    if len(set(jogo)) != len(jogo):
        raise ValueError("O jogo contém números repetidos")


def _obter_resultado(modalidade: Modalidade, concurso: int | None) -> Resultado:
    if concurso is None:
        resultado = buscar_resultado(modalidade)
        storage.salvar_resultado(resultado)
        return resultado

    resultado = storage.carregar_resultado(modalidade.chave, concurso)
    if resultado is not None:
        return resultado

    resultado = buscar_resultado(modalidade, concurso)
    storage.salvar_resultado(resultado)
    return resultado


def _encontrar_premio(resultado: Resultado, total_acertos: int) -> PremioFaixa | None:
    for premio in resultado.premios:
        if premio.acertos == total_acertos:
            return premio
    return None


def faixas_disponiveis(modalidade: Modalidade) -> list[tuple[int, str]]:
    """Lista as faixas de premiação (acertos, descrição) já vistas no histórico local,
    da maior para a menor. Usada para montar o filtro de faixas na interface."""
    historico = storage.carregar_historico(modalidade.chave)
    vistas: dict[int, str] = {}
    for resultado in historico:
        for premio in resultado.premios:
            if premio.acertos is not None:
                vistas[premio.acertos] = premio.descricao
    return sorted(vistas.items(), key=lambda item: item[0], reverse=True)


def conferir(modalidade: Modalidade, jogo: list[int], concurso: int | None = None) -> ResultadoConferencia:
    _validar_jogo(modalidade, jogo)
    resultado = _obter_resultado(modalidade, concurso)
    acertos = sorted(set(jogo) & set(resultado.dezenas))
    premio = _encontrar_premio(resultado, len(acertos))
    return ResultadoConferencia(
        concurso=resultado.concurso,
        data=resultado.data,
        dezenas_sorteadas=resultado.dezenas,
        acertos=acertos,
        premio=premio,
    )


def conferir_no_historico(
    modalidade: Modalidade,
    jogo: list[int],
    faixas_permitidas: set[int] | None = None,
) -> list[Ganho]:
    """Confere o jogo contra todo o histórico local e retorna em quais concursos
    ele teria batido alguma faixa de premiação, e quanto teria pago em cada um.

    `faixas_permitidas`, se informado, restringe a busca a essas quantidades de
    acertos (ex: {4, 5, 6} só considera faixas de 4 a 6 acertos). Por padrão
    (None) qualquer faixa paga conta, não só a principal.
    """
    _validar_jogo(modalidade, jogo)
    historico = storage.carregar_historico(modalidade.chave)
    if not historico:
        raise ValueError(
            f"Sem histórico local para {modalidade.nome}. Rode a sincronização primeiro."
        )

    jogo_set = set(jogo)
    ganhos: list[Ganho] = []
    for resultado in historico:
        n_acertos = len(jogo_set & set(resultado.dezenas))
        if faixas_permitidas is not None and n_acertos not in faixas_permitidas:
            continue
        premio = _encontrar_premio(resultado, n_acertos)
        if premio is not None:
            ganhos.append(
                Ganho(
                    concurso=resultado.concurso,
                    data=resultado.data,
                    acertos=n_acertos,
                    descricao_faixa=premio.descricao,
                    valor=premio.valor,
                )
            )
    return ganhos
