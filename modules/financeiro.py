"""
Módulo Inteligência Financeira — análise detalhada da saúde financeira.
Margem de lucro, ponto de equilíbrio, ROI por máquina, projeção de quitação e sazonalidade.
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import date
from dateutil.relativedelta import relativedelta

from database import (
    faturamento_mes,
    despesas_mes,
    num_locacoes_mes,
    ticket_medio,
    get_config,
    faturamento_por_equipamento,
    parcelas_pagas_equipamento,
    listar_equipamentos,
    listar_parcelas_equipamento,
    listar_parcelas,
)

# ──────────────────────────────────────────────
# Cores padrão
# ──────────────────────────────────────────────
COR_ESCURA = "#1B3A8C"
COR_CLARA = "#2B8BE8"


def _formatar_brl(valor):
    """Formata valor como R$ X.XXX,XX."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mes_label(mes_str):
    """Converte 'YYYY-MM' em rótulo legível, ex: 'Mar/2026'."""
    meses = {
        "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
        "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
        "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
    }
    ano = mes_str[:4]
    num = mes_str[5:7]
    return f"{meses.get(num, num)}/{ano}"


def render():
    st.markdown("# 📈 Inteligência Financeira")
    st.markdown("### Análise detalhada da saúde financeira")

    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")

    # ──────────────────────────────────────────────
    # 1. Margem de lucro real por mês (últimos 12 meses)
    # ──────────────────────────────────────────────
    st.subheader("Margem de lucro real por mês")

    meses_12 = []
    for i in range(11, -1, -1):
        dt = hoje - relativedelta(months=i)
        meses_12.append(dt.strftime("%Y-%m"))

    linhas = []
    for mes in meses_12:
        receita = faturamento_mes(mes)
        despesa = despesas_mes(mes)
        lucro = receita - despesa
        margem = (lucro / receita * 100) if receita > 0 else 0.0
        linhas.append({
            "Mês": _mes_label(mes),
            "Receita": _formatar_brl(receita),
            "Despesas": _formatar_brl(despesa),
            "Lucro": _formatar_brl(lucro),
            "Margem (%)": f"{margem:.1f}%",
        })

    st.table(linhas)

    # ──────────────────────────────────────────────
    # 2. Ponto de equilíbrio mensal (break-even)
    # ──────────────────────────────────────────────
    st.subheader("Ponto de equilíbrio mensal")

    parcelas_mes_valor = 0.0
    todas_parcelas = listar_parcelas(mes=mes_atual)
    for p in todas_parcelas:
        parcelas_mes_valor += p["valor"]

    reserva_manutencao = float(get_config("reserva_manutencao", "0"))
    custos_fixos = parcelas_mes_valor + reserva_manutencao

    tk_medio = ticket_medio()
    locacoes_realizadas = num_locacoes_mes(mes_atual)

    if tk_medio > 0:
        break_even = custos_fixos / tk_medio
        break_even_int = int(break_even) + (1 if break_even % 1 > 0 else 0)
    else:
        break_even_int = 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Custos fixos do mês", _formatar_brl(custos_fixos))
    col2.metric("Ticket médio", _formatar_brl(tk_medio))
    col3.metric("Locações necessárias", break_even_int)

    if tk_medio > 0:
        st.info(
            f"Você precisa de **{break_even_int} locações** para cobrir os custos fixos. "
            f"Já realizou **{locacoes_realizadas}** este mês."
        )
    else:
        st.warning("Não há dados suficientes para calcular o ponto de equilíbrio.")

    # ──────────────────────────────────────────────
    # 3. ROI por máquina
    # ──────────────────────────────────────────────
    st.subheader("ROI por máquina")

    equipamentos = listar_equipamentos()
    if equipamentos:
        for eq in equipamentos:
            eq_id = eq["id"]
            nome = eq["nome"]
            custo_aquisicao = float(eq["custo_aquisicao"]) if eq["custo_aquisicao"] else 0.0
            receita_total = faturamento_por_equipamento(eq_id)
            parcelas_pagas = parcelas_pagas_equipamento(eq_id)

            with st.expander(f"🔧 {nome}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("Custo de aquisição", _formatar_brl(custo_aquisicao))
                c2.metric("Receita total", _formatar_brl(receita_total))
                c3.metric("Parcelas pagas", _formatar_brl(parcelas_pagas))

                if custo_aquisicao > 0:
                    progresso = min(receita_total / custo_aquisicao, 1.0)
                    roi_pct = (receita_total / custo_aquisicao) * 100

                    if receita_total >= custo_aquisicao:
                        st.success(
                            f"✅ Máquina já se pagou! ROI: {roi_pct:.1f}% "
                            f"(retorno de {_formatar_brl(receita_total - custo_aquisicao)} acima do custo)"
                        )
                    else:
                        falta = custo_aquisicao - receita_total
                        st.warning(f"Faltam {_formatar_brl(falta)} para esta máquina se pagar.")

                    st.progress(progresso, text=f"{roi_pct:.1f}% do custo de aquisição recuperado")
                else:
                    st.caption("Custo de aquisição não informado.")
    else:
        st.info("Nenhum equipamento cadastrado.")

    # ──────────────────────────────────────────────
    # 4. Projeção de quitação
    # ──────────────────────────────────────────────
    st.subheader("Projeção de quitação de parcelas")

    parcelas_equip = listar_parcelas_equipamento()
    if parcelas_equip:
        for pe in parcelas_equip:
            pe_id = pe["id"]
            nome_equip = pe["nome_equipamento"]
            valor_total = float(pe["valor_total"])
            parcelas_lista = listar_parcelas(parcela_equip_id=pe_id)

            total_pago = sum(float(p["valor"]) for p in parcelas_lista if p["paga"])
            restante = valor_total - total_pago

            datas_vencimento = [p["data_vencimento"] for p in parcelas_lista if not p["paga"]]
            if datas_vencimento:
                ultima_parcela = max(datas_vencimento)
            else:
                ultima_parcela = None

            with st.expander(f"💳 {nome_equip} — {_formatar_brl(valor_total)}"):
                c1, c2 = st.columns(2)
                c1.metric("Já pago", _formatar_brl(total_pago))
                c2.metric("Restante", _formatar_brl(restante))

                if ultima_parcela:
                    st.info(f"📅 Data estimada de quitação: **{ultima_parcela}**")
                else:
                    st.success("✅ Todas as parcelas foram pagas!")

                num_total = len(parcelas_lista)
                num_pagas = sum(1 for p in parcelas_lista if p["paga"])
                if num_total > 0:
                    st.progress(
                        num_pagas / num_total,
                        text=f"{num_pagas}/{num_total} parcelas pagas",
                    )
    else:
        st.info("Nenhum parcelamento de equipamento cadastrado.")

    # ──────────────────────────────────────────────
    # 5. Análise de sazonalidade
    # ──────────────────────────────────────────────
    st.subheader("Análise de sazonalidade")

    # Coletar dados dos últimos 24 meses para ter visão ampla
    meses_saz = []
    for i in range(23, -1, -1):
        dt = hoje - relativedelta(months=i)
        meses_saz.append(dt.strftime("%Y-%m"))

    labels = []
    valores = []
    for mes in meses_saz:
        n = num_locacoes_mes(mes)
        if n > 0 or labels:  # só começa a exibir a partir do primeiro mês com dados
            labels.append(_mes_label(mes))
            valores.append(n)

    if valores and max(valores) > 0:
        melhor_idx = valores.index(max(valores))
        pior_idx = valores.index(min(valores))

        cores = []
        for i in range(len(valores)):
            if i == melhor_idx:
                cores.append("#2ECC71")  # verde para melhor mês
            elif i == pior_idx:
                cores.append("#E74C3C")  # vermelho para pior mês
            else:
                cores.append(COR_CLARA)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=labels,
            y=valores,
            marker_color=cores,
            text=valores,
            textposition="auto",
            name="Locações",
        ))
        fig.update_layout(
            title="Locações por mês",
            xaxis_title="Mês",
            yaxis_title="Nº de locações",
            plot_bgcolor="white",
            font=dict(color=COR_ESCURA),
            xaxis=dict(tickangle=-45),
        )
        st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        c1.metric(
            f"🏆 Melhor mês: {labels[melhor_idx]}",
            f"{valores[melhor_idx]} locações",
        )
        c2.metric(
            f"📉 Pior mês: {labels[pior_idx]}",
            f"{valores[pior_idx]} locações",
        )
    else:
        st.info("Não há dados de locações suficientes para análise de sazonalidade.")
