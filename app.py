"""Interface Streamlit: Análise, Concursos, Gerador e Conferidor de jogos das loterias da Caixa."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from loteria import analysis, checker, generator, modalidades, storage, sync
from loteria.api import ErroApiCaixa
from loteria.sync import SincronizacaoParcial

st.set_page_config(page_title="Loterias da Caixa", layout="wide")

if os.environ.get("LOTERIAS_DESKTOP"):
    # Rodando dentro da janela nativa do .exe: some só com o botão "Deploy" e
    # o menu "⋮", que não fazem sentido num app desktop. Importante: NÃO
    # esconder o container inteiro (`stToolbar`) — em algumas versões do
    # Streamlit ele também hospeda o controle de reabrir o menu lateral
    # quando colapsado, e escondê-lo travava esse botão para sempre.
    st.markdown(
        "<style>"
        "[data-testid='stAppDeployButton'] {display: none;}"
        "[data-testid='stMainMenu'] {display: none;}"
        "</style>",
        unsafe_allow_html=True,
    )

st.title("🎲 Loterias da Caixa")

nomes_para_chave = {m.nome: m.chave for m in modalidades.TODAS}
nome_escolhido = st.sidebar.selectbox("Modalidade", list(nomes_para_chave.keys()))
modalidade = modalidades.obter(nomes_para_chave[nome_escolhido])
st.sidebar.caption(
    f"Escolha {modalidade.qtd_numeros_por_jogo} números entre "
    f"{modalidade.numero_min} e {modalidade.numero_max}."
)

aba_analise, aba_concursos, aba_gerador, aba_conferidor = st.tabs(
    ["📊 Análise", "🔍 Concursos", "🎯 Gerador", "✅ Conferidor"]
)


def _parse_jogo(texto: str) -> list[int]:
    partes = [p.strip() for p in texto.replace(";", ",").split(",") if p.strip()]
    return [int(p) for p in partes]


def _fmt_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _df_premios(premios) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "faixa": p.descricao,
                "ganhadores": p.ganhadores,
                "prêmio por ganhador": _fmt_moeda(p.valor),
                "total pago na faixa": _fmt_moeda(p.valor * p.ganhadores),
            }
            for p in premios
        ]
    )


def _seletor_faixas(modalidade, key: str) -> set[int] | None:
    """Multiselect com as faixas de premiação já vistas no histórico local.
    Retorna None (= todas as faixas) se nada for selecionado."""
    faixas = checker.faixas_disponiveis(modalidade)
    if not faixas:
        return None
    mapa_descricao_para_acertos = {descricao: acertos for acertos, descricao in faixas}
    selecionadas = st.multiselect(
        "Filtrar por faixa de acertos (vazio = considera todas)",
        options=[descricao for _, descricao in faixas],
        default=[],
        key=key,
    )
    if not selecionadas:
        return None
    return {mapa_descricao_para_acertos[d] for d in selecionadas}


def _resumo_ganhos_historico(modalidade, jogo, faixas_permitidas: set[int] | None = None) -> None:
    """Mostra, para um jogo já gerado, quantas vezes ele teria ganho algo no histórico local."""
    try:
        ganhos = checker.conferir_no_historico(modalidade, jogo, faixas_permitidas=faixas_permitidas)
    except ValueError:
        st.caption("Sincronize o histórico na aba Análise para ver isso.")
        return
    if not ganhos:
        st.caption("Não teria ganho nenhuma faixa de premiação nos concursos já baixados.")
        return
    total = sum(g.valor for g in ganhos)
    with st.expander(f"🕐 Já teria ganho em {len(ganhos)} concurso(s) — total {_fmt_moeda(total)}"):
        st.table(
            pd.DataFrame(
                [
                    {
                        "concurso": g.concurso,
                        "data": g.data,
                        "acertos": g.acertos,
                        "faixa": g.descricao_faixa,
                        "valor": _fmt_moeda(g.valor),
                    }
                    for g in ganhos
                ]
            )
        )


with aba_analise:
    st.subheader(f"Análise de resultados — {modalidade.nome}")

    col_sync1, col_sync2 = st.columns(2)

    with col_sync1:
        if st.button("🔄 Sincronizar (baixar concursos novos)"):
            barra = st.progress(0.0, text="Sincronizando...")

            def _progresso(atual: int, total: int) -> None:
                barra.progress(min(atual / total, 1.0), text=f"Baixando {atual}/{total} concurso(s)...")

            try:
                baixados = sync.sincronizar(modalidade, progresso=_progresso)
                barra.empty()
                st.success(f"{baixados} concurso(s) baixado(s).")
            except SincronizacaoParcial as parcial:
                barra.empty()
                st.warning(f"⚠️ Parou no meio: {parcial}")
            except ErroApiCaixa as erro:
                barra.empty()
                st.error(f"Erro ao consultar a API da Caixa: {erro}")

    with col_sync2:
        confirmar_wipe = st.checkbox(f"Confirmo apagar o cache local de {modalidade.nome}")
        if st.button("🗑️ Apagar cache e ressincronizar tudo", disabled=not confirmar_wipe):
            barra = st.progress(0.0, text="Ressincronizando do zero...")

            def _progresso_wipe(atual: int, total: int) -> None:
                barra.progress(min(atual / total, 1.0), text=f"Baixando {atual}/{total} concurso(s)...")

            try:
                baixados = sync.ressincronizar_do_zero(modalidade, progresso=_progresso_wipe)
                barra.empty()
                st.success(f"{baixados} concurso(s) baixado(s) do zero.")
            except SincronizacaoParcial as parcial:
                barra.empty()
                st.warning(f"⚠️ Parou no meio: {parcial}")
            except ErroApiCaixa as erro:
                barra.empty()
                st.error(f"Erro ao consultar a API da Caixa: {erro}")
        st.caption(
            "Use isso se os dados parecerem incompletos ou desatualizados "
            "(ex: sem informação de premiação em concursos antigos)."
        )

    try:
        estatisticas = analysis.calcular_estatisticas(modalidade)
    except ValueError as erro:
        st.info(str(erro))
    else:
        historico = storage.carregar_historico(modalidade.chave)
        ultimo = historico[-1]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Concursos no histórico", estatisticas.total_concursos)
        col2.metric("Média de pares por sorteio", f"{estatisticas.media_pares:.1f}")
        col3.metric("Soma média das dezenas", f"{estatisticas.media_soma:.0f}")
        col4.metric(f"Acumulado p/ concurso {ultimo.concurso + 1}", _fmt_moeda(ultimo.valor_acumulado_proximo))
        st.caption(f"Último resultado: concurso {ultimo.concurso} em {ultimo.data}. Próximo sorteio: {ultimo.data_proximo_concurso}.")

        st.markdown("**Premiação do último concurso sincronizado**")
        st.table(_df_premios(ultimo.premios))

        st.markdown("**Frequência por dezena**")
        df_freq = pd.DataFrame(
            sorted(estatisticas.frequencia.items()), columns=["dezena", "vezes_sorteada"]
        ).set_index("dezena")
        st.bar_chart(df_freq)

        st.markdown("**Atraso por dezena (concursos sem sair)**")
        df_atraso = pd.DataFrame(
            sorted(estatisticas.atraso.items()), columns=["dezena", "concursos_sem_sair"]
        ).set_index("dezena")
        st.bar_chart(df_atraso)

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("**Mais sorteadas**")
            st.table(pd.DataFrame(analysis.mais_sorteadas(estatisticas), columns=["dezena", "vezes"]))
        with col_b:
            st.markdown("**Menos sorteadas**")
            st.table(pd.DataFrame(analysis.menos_sorteadas(estatisticas), columns=["dezena", "vezes"]))
        with col_c:
            st.markdown("**Mais atrasadas**")
            st.table(pd.DataFrame(analysis.mais_atrasadas(estatisticas), columns=["dezena", "concursos"]))


with aba_concursos:
    st.subheader(f"Detalhes de concursos — {modalidade.nome}")

    primeiro = storage.primeiro_concurso_salvo(modalidade.chave)
    ultimo_num = storage.ultimo_concurso_salvo(modalidade.chave)

    if primeiro is None:
        st.info("Sem histórico local. Sincronize na aba Análise primeiro.")
    else:
        concurso_escolhido = st.number_input(
            "Número do concurso",
            min_value=primeiro,
            max_value=ultimo_num,
            value=ultimo_num,
            step=1,
        )
        resultado = storage.carregar_resultado(modalidade.chave, int(concurso_escolhido))
        if resultado is None:
            st.warning("Esse concurso não está no cache local (pode ter sido pulado). Sincronize novamente.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric("Concurso", resultado.concurso)
            col2.metric("Data do sorteio", resultado.data)
            col3.metric("Acumulou?", "Sim" if resultado.acumulado else "Não")

            st.markdown("**Dezenas sorteadas**")
            st.code(" - ".join(f"{n:02d}" for n in resultado.dezenas), language=None)

            st.markdown("**Premiação desse concurso**")
            st.table(_df_premios(resultado.premios))

            st.caption(
                f"Próximo concurso ({resultado.concurso + 1}) em {resultado.data_proximo_concurso}, "
                f"acumulado estimado: {_fmt_moeda(resultado.valor_acumulado_proximo)}."
            )

        st.markdown("---")
        st.markdown("**Todos os concursos baixados**")
        historico_completo = storage.carregar_historico(modalidade.chave)
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "concurso": r.concurso,
                        "data": r.data,
                        "dezenas": ", ".join(f"{n:02d}" for n in r.dezenas),
                        "acumulou": "Sim" if r.acumulado else "Não",
                        "acumulado próx. concurso": _fmt_moeda(r.valor_acumulado_proximo),
                    }
                    for r in reversed(historico_completo)
                ]
            ),
            use_container_width=True,
            height=400,
        )


with aba_gerador:
    st.subheader(f"Gerador de jogos — {modalidade.nome}")

    estrategia = st.radio(
        "Estratégia",
        options=list(generator.ESTRATEGIAS),
        format_func=lambda e: "Aleatório" if e == "aleatorio" else "Ponderado pela frequência histórica",
        horizontal=True,
    )
    n_jogos = st.number_input("Quantidade de jogos", min_value=1, max_value=1000, value=1, step=1)
    evitar_repetidos = st.checkbox("Evitar jogos repetidos entre si", value=True)
    checar_historico = st.checkbox("Checar se cada jogo já teria ganho algo no histórico", value=True)
    faixas_gerador = _seletor_faixas(modalidade, key="faixas_gerador") if checar_historico else None

    if st.button("🎲 Gerar"):
        try:
            jogos = generator.gerar_jogo(
                modalidade,
                estrategia=estrategia,
                n_jogos=int(n_jogos),
                evitar_repetidos=evitar_repetidos,
            )
        except ValueError as erro:
            st.info(str(erro))
        except RuntimeError as erro:
            st.error(str(erro))
        else:
            for jogo in jogos:
                st.code(" - ".join(f"{n:02d}" for n in jogo), language=None)
                if checar_historico:
                    _resumo_ganhos_historico(modalidade, jogo, faixas_permitidas=faixas_gerador)


with aba_conferidor:
    st.subheader(f"Conferidor de jogos — {modalidade.nome}")

    texto_jogos = st.text_area(
        "Um jogo por linha, números separados por vírgula",
        placeholder="04, 09, 15, 23, 33, 41",
    )
    usar_ultimo = st.checkbox("Usar o último concurso disponível", value=True)
    concurso_manual = None
    if not usar_ultimo:
        concurso_manual = st.number_input("Número do concurso", min_value=1, step=1)

    col_conferir, col_historico = st.columns(2)

    with col_conferir:
        if st.button("✅ Conferir num concurso"):
            linhas = [linha for linha in texto_jogos.splitlines() if linha.strip()]
            if not linhas:
                st.info("Informe pelo menos um jogo.")
            for linha in linhas:
                try:
                    jogo = _parse_jogo(linha)
                    resultado = checker.conferir(
                        modalidade, jogo, concurso=None if usar_ultimo else int(concurso_manual)
                    )
                except (ValueError, ErroApiCaixa) as erro:
                    st.error(f"`{linha}` → {erro}")
                    continue
                st.write(
                    f"Jogo `{jogo}` no concurso **{resultado.concurso}** ({resultado.data}): "
                    f"**{resultado.total_acertos} acerto(s)** — {resultado.acertos}"
                )
                if resultado.premio is not None and resultado.valor_ganho > 0:
                    st.success(
                        f"🏆 Faixa \"{resultado.premio.descricao}\": você ganharia "
                        f"**{_fmt_moeda(resultado.valor_ganho)}** "
                        f"({resultado.premio.ganhadores} ganhador(es) reais nesse concurso)."
                    )
                elif resultado.premio is not None:
                    st.warning(
                        f"Você bateria a faixa \"{resultado.premio.descricao}\", mas ninguém "
                        "ganhou nesse concurso (prêmio acumulou)."
                    )
                else:
                    st.info("Sem prêmio nesse concurso.")

    with col_historico:
        faixas_conferidor = _seletor_faixas(modalidade, key="faixas_conferidor")
        if st.button("📜 Conferir em todo o histórico"):
            linhas = [linha for linha in texto_jogos.splitlines() if linha.strip()]
            if not linhas:
                st.info("Informe pelo menos um jogo.")
            for linha in linhas:
                try:
                    jogo = _parse_jogo(linha)
                    ganhos = checker.conferir_no_historico(modalidade, jogo, faixas_permitidas=faixas_conferidor)
                except (ValueError, ErroApiCaixa) as erro:
                    st.error(f"`{linha}` → {erro}")
                    continue
                st.markdown(f"**Jogo `{jogo}`** — checa **qualquer** faixa de premiação selecionada, não só a principal")
                if not ganhos:
                    st.info("Não teria ganho nenhuma faixa de premiação no histórico sincronizado.")
                    continue
                df_ganhos = pd.DataFrame(
                    [
                        {
                            "concurso": g.concurso,
                            "data": g.data,
                            "acertos": g.acertos,
                            "faixa": g.descricao_faixa,
                            "valor": _fmt_moeda(g.valor),
                        }
                        for g in ganhos
                    ]
                )
                st.table(df_ganhos)
                total = sum(g.valor for g in ganhos)
                st.success(f"Total que você teria ganhado no histórico: **{_fmt_moeda(total)}**")
