"""Sincroniza o cache local (SQLite) com a API da Caixa.

Os concursos faltantes são baixados em paralelo (a API é uma consulta HTTP simples
por concurso, então isso reduz bastante o tempo para modalidades com milhares de
concursos, como Lotofácil ou Quina). A detecção de "o que falta baixar" é feita por
diferença de conjuntos (todos os concursos de 1 até o mais recente, menos os que já
estão salvos) — não apenas pelo maior concurso salvo — porque a API às vezes começa
a recusar requisições no meio de uma sincronização grande, o que pode deixar buracos
no meio do histórico mesmo com o concurso mais recente já salvo.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import storage
from .api import ErroApiCaixa, buscar_resultado
from .modalidades import Modalidade

PARALELISMO_PADRAO = 5
# Se a API começar a recusar várias requisições seguidas (bloqueio/limite de taxa),
# paramos de insistir em vez de gastar minutos falhando concurso por concurso.
FALHAS_SEGUIDAS_LIMITE = 8


class SincronizacaoParcial(Exception):
    """A sincronização parou antes de terminar (ex: a API começou a recusar requisições).

    O que já foi baixado até aqui foi salvo normalmente; rodar a sincronização de
    novo mais tarde retoma exatamente dos concursos que faltaram, não do zero.
    """

    def __init__(self, baixados: int, mensagem: str):
        super().__init__(mensagem)
        self.baixados = baixados


def _concursos_faltantes(modalidade: Modalidade, ate_concurso: int) -> list[int]:
    salvos = storage.concursos_salvos(modalidade.chave)
    return [c for c in range(1, ate_concurso) if c not in salvos]


def sincronizar(
    modalidade: Modalidade,
    progresso: Callable[[int, int], None] | None = None,
    paralelismo: int = PARALELISMO_PADRAO,
) -> int:
    """Baixa e salva localmente todos os concursos ainda não cacheados.

    Retorna a quantidade de concursos baixados. `progresso`, se fornecido, é
    chamado a cada concurso baixado com (quantidade_baixada, total_a_baixar).
    Levanta `SincronizacaoParcial` (com o total já baixado) se a API começar a
    recusar requisições repetidamente antes de terminar.
    """
    resultado_atual = buscar_resultado(modalidade)
    ultimo_remoto = resultado_atual.concurso

    faltantes = _concursos_faltantes(modalidade, ultimo_remoto)
    total = len(faltantes) + 1
    baixados = 0

    storage.salvar_resultado(resultado_atual)
    baixados += 1
    if progresso:
        progresso(baixados, total)

    if not faltantes:
        return baixados

    falhas_seguidas = 0
    with ThreadPoolExecutor(max_workers=paralelismo) as executor:
        futuros = {executor.submit(buscar_resultado, modalidade, c): c for c in faltantes}
        try:
            for futuro in as_completed(futuros):
                try:
                    resultado = futuro.result()
                except ErroApiCaixa:
                    falhas_seguidas += 1
                    if falhas_seguidas >= FALHAS_SEGUIDAS_LIMITE:
                        raise SincronizacaoParcial(
                            baixados,
                            f"A API da Caixa começou a recusar requisições (após {baixados} "
                            f"concurso(s) baixados nessa rodada). Isso costuma ser bloqueio "
                            "temporário por excesso de requisições — espere alguns minutos e "
                            "clique em sincronizar de novo; ele retoma de onde parou.",
                        )
                    continue
                else:
                    falhas_seguidas = 0
                    storage.salvar_resultado(resultado)
                    baixados += 1
                    if progresso:
                        progresso(baixados, total)
        finally:
            for futuro in futuros:
                futuro.cancel()

    return baixados


def ressincronizar_do_zero(
    modalidade: Modalidade,
    progresso: Callable[[int, int], None] | None = None,
    paralelismo: int = PARALELISMO_PADRAO,
) -> int:
    """Apaga o cache local da modalidade e baixa tudo de novo.

    Útil para corrigir concursos salvos por uma versão antiga do schema (sem
    dados de premiação, por exemplo) — a sincronização incremental normal não
    reprocessa concursos que já estão salvos, só os que faltam.
    """
    storage.apagar_modalidade(modalidade.chave)
    return sincronizar(modalidade, progresso=progresso, paralelismo=paralelismo)
