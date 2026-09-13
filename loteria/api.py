"""Cliente para a API pública de resultados da Caixa.

Usa o serviço não-oficial (mas amplamente usado) em
https://servicebus2.caixa.gov.br/portaldeloterias/api/{modalidade}[/{concurso}]
"""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass

import requests

from .modalidades import Modalidade

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api"
TIMEOUT_SEGUNDOS = 10
TENTATIVAS = 4
ESPERA_BASE_SEGUNDOS = 1.5      # dobra a cada tentativa (backoff exponencial) + jitter
ESPERA_MAXIMA_SEGUNDOS = 20.0
STATUS_BLOQUEIO = {429, 403}    # a API costuma responder assim quando está limitando taxa de requisições

# Só casa descrições "puras" tipo "6 acertos" ou "0 acertos" — deliberadamente NÃO casa
# faixas com critério extra, como "6 acertos + 2 trevos" (+Milionária), porque nesses
# casos a quantidade de acertos sozinha não identifica a faixa: duas faixas diferentes
# (com/sem trevo) têm a mesma contagem de acertos, e não conferimos trevos/time do
# coração. Deixar acertos=None nesses casos evita atribuir o valor da faixa errada.
_PADRAO_ACERTOS = re.compile(r"^\s*(\d+)\s*acertos?\s*$", re.IGNORECASE)


class ErroApiCaixa(Exception):
    pass


@dataclass(frozen=True)
class PremioFaixa:
    faixa: int
    descricao: str          # ex: "6 acertos" (texto original da Caixa)
    acertos: int | None      # quantidade de acertos exigida, extraída da descrição (None se não numérico, ex: trevos)
    ganhadores: int
    valor: float              # valor pago a cada ganhador dessa faixa nesse concurso


@dataclass(frozen=True)
class Resultado:
    modalidade: str
    concurso: int
    data: str
    dezenas: list[int]
    acumulado: bool
    valor_acumulado_proximo: float
    data_proximo_concurso: str
    premios: list[PremioFaixa]


def _requisitar(url: str) -> dict:
    ultimo_erro: Exception | None = None
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            resposta = requests.get(url, timeout=TIMEOUT_SEGUNDOS, headers={"User-Agent": "Mozilla/5.0"})
            if resposta.status_code in STATUS_BLOQUEIO:
                raise requests.HTTPError(f"HTTP {resposta.status_code} (limite de requisições?)", response=resposta)
            resposta.raise_for_status()
            resposta.encoding = "latin-1"  # a API da Caixa envia acentos em latin-1, não utf-8
            return resposta.json()
        except (requests.RequestException, ValueError) as erro:
            ultimo_erro = erro
            if tentativa < TENTATIVAS:
                espera = min(ESPERA_BASE_SEGUNDOS * (2 ** (tentativa - 1)), ESPERA_MAXIMA_SEGUNDOS)
                espera += random.uniform(0, espera * 0.3)
                time.sleep(espera)
    raise ErroApiCaixa(f"Falha ao consultar {url}: {ultimo_erro}")


def _normalizar_premio(bruto: dict) -> PremioFaixa:
    descricao = str(bruto.get("descricaoFaixa", ""))
    correspondencia = _PADRAO_ACERTOS.search(descricao)
    return PremioFaixa(
        faixa=int(bruto.get("faixa", 0)),
        descricao=descricao,
        acertos=int(correspondencia.group(1)) if correspondencia else None,
        ganhadores=int(bruto.get("numeroDeGanhadores", 0)),
        valor=float(bruto.get("valorPremio") or 0.0),
    )


def _normalizar(modalidade: Modalidade, bruto: dict) -> Resultado:
    dezenas_str = bruto.get("listaDezenas") or bruto.get("dezenasSorteadasOrdemSorteio") or []
    dezenas = sorted(int(d) for d in dezenas_str)
    premios = [_normalizar_premio(p) for p in bruto.get("listaRateioPremio") or []]
    return Resultado(
        modalidade=modalidade.chave,
        concurso=int(bruto["numero"]),
        data=str(bruto.get("dataApuracao", "")),
        dezenas=dezenas,
        acumulado=bool(bruto.get("acumulado", False)),
        valor_acumulado_proximo=float(bruto.get("valorAcumuladoProximoConcurso") or 0.0),
        data_proximo_concurso=str(bruto.get("dataProximoConcurso") or ""),
        premios=premios,
    )


def buscar_resultado(modalidade: Modalidade, concurso: int | None = None) -> Resultado:
    """Busca um resultado específico, ou o mais recente se concurso for None."""
    url = f"{BASE_URL}/{modalidade.slug_api}"
    if concurso is not None:
        url = f"{url}/{concurso}"
    bruto = _requisitar(url)
    return _normalizar(modalidade, bruto)


def buscar_ultimo_concurso(modalidade: Modalidade) -> int:
    return buscar_resultado(modalidade).concurso
