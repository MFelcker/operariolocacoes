"""
Módulo Dashboard — página inicial do sistema.
Exibe resumo mensal, gráficos, indicadores e alertas.
"""
import streamlit as st
import plotly.graph_objects as go
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from database import (
    faturamento_mes,
    despesas_mes,
    despesas_por_categoria_mes,
    num_locacoes_mes,
    taxa_ocupacao_mes,
    saldo_estoque,
    get_config,
    listar_parcelas,
    clientes_inativos,
    ticket_medio,
    listar_equipamentos,
)

# ──────────────────────────────────────────────
# Cores padrão
# ──────────────────────────────────────────────
COR_ESCURA = "#1B3A8C"
COR_CLARA = "#2B8BE8"


def _formatar_brl(valor):
    """Formata valor como R$ X.XXX,XX."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def render():
    st.title("📊 Dashboard")
    st.caption("Visão geral do mês atual")

    mes_atual = date.today().strftime("%Y-%m")

    # ──────────────────────────────────────────
    # 1. Cartões de resumo mensal
    # ──────────────────────────────────────────
    fat_bruto = faturamento_mes(mes_atual)
    desp_total = despesas_mes(mes_atual)
    lucro_real = fat_bruto - desp_total
    n_locacoes = num_locacoes_mes(mes_atual)

    ocupacao = taxa_ocupacao_mes(mes_atual)
    equipamentos = listar_equipamentos()
    total_equips = len(equipamentos)
    if total_equips > 0:
        # Equipamentos sem locação no mês têm 0% de ocupação
        soma_ocupacao = sum(ocupacao.get(e["id"], 0) for e in equipamentos)
        taxa_media = round(soma_ocupacao / total_equips, 1)
    else:
        taxa_media = 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Faturamento Bruto", _formatar_brl(fat_bruto))
    with c2:
        st.metric("Lucro Real Estimado", _formatar_brl(lucro_real))
    with c3:
        st.metric("Nº de Locações", n_locacoes)
    with c4:
        st.metric("Taxa de Ocupação Média", f"{taxa_media}%")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 2. Gráfico de barras — Faturamento vs Lucro (últimos 6 meses)
    # ──────────────────────────────────────────
    col_grafico1, col_grafico2 = st.columns(2)

    with col_grafico1:
        st.subheader("Faturamento vs Lucro — Últimos 6 meses")

        meses_labels = []
        faturamentos = []
        lucros = []

        for i in range(5, -1, -1):
            dt = date.today() - relativedelta(months=i)
            m = dt.strftime("%Y-%m")
            fat = faturamento_mes(m)
            desp = despesas_mes(m)
            meses_labels.append(dt.strftime("%m/%Y"))
            faturamentos.append(round(fat, 2))
            lucros.append(round(fat - desp, 2))

        fig_barras = go.Figure()
        fig_barras.add_trace(go.Bar(
            name="Faturamento Bruto",
            x=meses_labels,
            y=faturamentos,
            marker_color=COR_ESCURA,
            text=[_formatar_brl(v) for v in faturamentos],
            textposition="outside",
        ))
        fig_barras.add_trace(go.Bar(
            name="Lucro Real",
            x=meses_labels,
            y=lucros,
            marker_color=COR_CLARA,
            text=[_formatar_brl(v) for v in lucros],
            textposition="outside",
        ))
        fig_barras.update_layout(
            barmode="group",
            xaxis_title="Mês",
            yaxis_title="Valor (R$)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=40),
            height=400,
        )
        st.plotly_chart(fig_barras, use_container_width=True)

    # ──────────────────────────────────────────
    # 3. Gráfico de pizza — Composição de despesas do mês
    # ──────────────────────────────────────────
    with col_grafico2:
        st.subheader("Composição de Despesas — Mês Atual")

        categorias_map = {
            "parcelas": "Parcelas",
            "sabao": "Sabão",
            "gasolina": "Gasolina",
            "manutencao": "Manutenção",
            "outros": "Outros",
        }
        desp_cat = despesas_por_categoria_mes(mes_atual)

        labels = []
        valores = []
        for chave, nome in categorias_map.items():
            val = desp_cat.get(chave, 0)
            if val > 0:
                labels.append(nome)
                valores.append(round(val, 2))

        if valores:
            cores_pizza = [COR_ESCURA, COR_CLARA, "#4DA8F0", "#7FC4F8", "#B0D9FB"]
            fig_pizza = go.Figure(data=[go.Pie(
                labels=labels,
                values=valores,
                marker=dict(colors=cores_pizza[:len(labels)]),
                textinfo="label+percent",
                hovertemplate="%{label}: R$ %{value:,.2f}<extra></extra>",
            )])
            fig_pizza.update_layout(
                margin=dict(l=20, r=20, t=40, b=40),
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Nenhuma despesa registrada neste mês.")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 4. Indicador de estoque de sabão
    # ──────────────────────────────────────────
    col_ind1, col_ind2, col_ind3 = st.columns(3)

    with col_ind1:
        st.subheader("🧴 Estoque de Sabão")
        estoque_atual = saldo_estoque()
        estoque_minimo = int(get_config("estoque_minimo_ml", "2000"))

        st.metric("Estoque Atual", f"{estoque_atual} ml")
        if estoque_atual < estoque_minimo:
            st.warning(
                f"⚠️ Estoque abaixo do mínimo! "
                f"Atual: {estoque_atual} ml | Mínimo: {estoque_minimo} ml"
            )
        else:
            st.success(f"✅ Estoque dentro do nível seguro (mínimo: {estoque_minimo} ml)")

    # ──────────────────────────────────────────
    # 5. Previsão de faturamento do próximo mês
    # ──────────────────────────────────────────
    with col_ind2:
        st.subheader("🔮 Previsão Próximo Mês")
        fat_ultimos_3 = []
        for i in range(1, 4):
            dt = date.today() - relativedelta(months=i)
            m = dt.strftime("%Y-%m")
            fat_ultimos_3.append(faturamento_mes(m))

        if any(v > 0 for v in fat_ultimos_3):
            previsao = round(sum(fat_ultimos_3) / 3, 2)
            st.metric("Faturamento Estimado", _formatar_brl(previsao))
            st.caption("Média dos últimos 3 meses")
        else:
            st.info("Dados insuficientes para previsão.")

    # ──────────────────────────────────────────
    # 6. Indicador de ponto de equilíbrio (break-even)
    # ──────────────────────────────────────────
    with col_ind3:
        st.subheader("⚖️ Ponto de Equilíbrio")
        tk_medio = ticket_medio()

        if tk_medio > 0:
            locacoes_necessarias = int(-(-desp_total // tk_medio))  # ceil division
            st.metric("Locações Realizadas", f"{n_locacoes} / {locacoes_necessarias}")

            if n_locacoes >= locacoes_necessarias:
                st.success("✅ Custos fixos cobertos!")
            else:
                faltam = locacoes_necessarias - n_locacoes
                st.warning(f"⚠️ Faltam {faltam} locação(ões) para cobrir os custos.")

            st.caption(f"Ticket médio: {_formatar_brl(tk_medio)}")
        else:
            st.info("Sem locações registradas para calcular ticket médio.")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 7. Seção de alertas
    # ──────────────────────────────────────────
    st.subheader("🔔 Alertas")

    alertas = []

    # Alerta: estoque baixo
    if estoque_atual < estoque_minimo:
        alertas.append(
            f"🧴 **Estoque de sabão baixo:** {estoque_atual} ml "
            f"(mínimo configurado: {estoque_minimo} ml)"
        )

    # Alerta: parcelas do mês
    parcelas_mes = listar_parcelas(mes=mes_atual)
    parcelas_pendentes = [p for p in parcelas_mes if not p["paga"]]
    if parcelas_pendentes:
        total_parcelas = sum(p["valor"] for p in parcelas_pendentes)
        alertas.append(
            f"💰 **{len(parcelas_pendentes)} parcela(s) pendente(s) este mês** "
            f"— Total: {_formatar_brl(total_parcelas)}"
        )
        for p in parcelas_pendentes:
            alertas.append(
                f"   - {p['nome_equipamento']} — Parcela {p['numero']}: "
                f"{_formatar_brl(p['valor'])} (venc. {p['data_vencimento']})"
            )

    # Alerta: clientes inativos
    dias_inativo = int(get_config("dias_cliente_inativo", "30"))
    inativos = clientes_inativos(dias_inativo)
    if inativos:
        alertas.append(
            f"👥 **{len(inativos)} cliente(s) inativo(s)** "
            f"(sem locação há mais de {dias_inativo} dias)"
        )
        for cli in inativos[:5]:  # mostrar no máximo 5
            alertas.append(
                f"   - {cli['nome']} — última locação: {cli['ultima_locacao']} "
                f"({cli['dias_sem_locacao']} dias)"
            )
        if len(inativos) > 5:
            alertas.append(f"   - ... e mais {len(inativos) - 5} cliente(s)")

    if alertas:
        for alerta in alertas:
            st.markdown(alerta)
    else:
        st.success("✅ Nenhum alerta no momento. Tudo em ordem!")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 8. Botão de ação rápida — Nova Locação
    # ──────────────────────────────────────────
    if st.button("➕ Nova Locação", type="primary", use_container_width=False):
        st.session_state["pagina"] = "📦 Locações"
        st.session_state["abrir_nova_locacao"] = True
        st.rerun()
