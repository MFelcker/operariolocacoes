"""
Módulo Marketing — gastos com publicidade, propaganda e métricas do Instagram.
Inclui controle de campanhas, análise de ROI de marketing e indicadores de redes sociais.
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from database import (
    listar_instagram_metricas,
    get_instagram_metrica,
    salvar_instagram_metrica,
    excluir_instagram_metrica,
    listar_campanhas,
    criar_campanha,
    atualizar_campanha,
    excluir_campanha,
    gastos_marketing_mes,
    faturamento_mes,
    num_locacoes_mes,
)

COR_ESCURA = "#1B3A8C"
COR_CLARA = "#2B8BE8"
COR_INSTAGRAM = "#E1306C"
COR_INSTAGRAM_LIGHT = "#F77737"


def _formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _mes_label(mes_str):
    meses = {
        "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
        "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
        "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
    }
    return f"{meses.get(mes_str[5:7], mes_str[5:7])}/{mes_str[:4]}"


def render():
    st.header("📣 Marketing e Redes Sociais")

    tab_visao, tab_instagram, tab_campanhas = st.tabs([
        "📊 Visão Geral",
        "📸 Instagram",
        "🎯 Campanhas",
    ])

    with tab_visao:
        _render_visao_geral()
    with tab_instagram:
        _render_instagram()
    with tab_campanhas:
        _render_campanhas()


# ══════════════════════════════════════════════
# TAB 1 — Visão Geral de Marketing
# ══════════════════════════════════════════════
def _render_visao_geral():
    st.subheader("Visão Geral de Marketing")

    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")

    # ── KPIs do mês atual ──
    gasto_mkt = gastos_marketing_mes(mes_atual)
    fat_mes = faturamento_mes(mes_atual)
    n_locacoes = num_locacoes_mes(mes_atual)

    # Buscar métricas do Instagram do mês
    ig_mes = get_instagram_metrica(mes_atual)
    seguidores = ig_mes["seguidores"] if ig_mes else 0
    novos_seg = ig_mes["seguidores_novos"] if ig_mes else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Gasto em Marketing", _formatar_brl(gasto_mkt))
    with c2:
        roi = ((fat_mes / gasto_mkt - 1) * 100) if gasto_mkt > 0 else 0
        st.metric("ROI do Marketing", f"{roi:.0f}%" if gasto_mkt > 0 else "—")
    with c3:
        cpa = gasto_mkt / n_locacoes if n_locacoes > 0 else 0
        st.metric("Custo por Locação", _formatar_brl(cpa) if n_locacoes > 0 else "—")
    with c4:
        custo_seg = gasto_mkt / novos_seg if novos_seg > 0 else 0
        st.metric("Custo por Seguidor", _formatar_brl(custo_seg) if novos_seg > 0 else "—")

    st.markdown("---")

    # ── Gráfico: Investimento em Marketing vs Faturamento (últimos 6 meses) ──
    st.subheader("Investimento em Marketing vs Faturamento")

    meses_labels = []
    gastos_mkt = []
    faturamentos = []
    locacoes_list = []

    for i in range(5, -1, -1):
        dt = hoje - relativedelta(months=i)
        m = dt.strftime("%Y-%m")
        meses_labels.append(_mes_label(m))
        gastos_mkt.append(gastos_marketing_mes(m))
        faturamentos.append(faturamento_mes(m))
        locacoes_list.append(num_locacoes_mes(m))

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(name="Gasto Marketing", x=meses_labels, y=gastos_mkt,
               marker_color=COR_INSTAGRAM, text=[_formatar_brl(v) for v in gastos_mkt],
               textposition="outside"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(name="Faturamento", x=meses_labels, y=faturamentos,
                   mode="lines+markers", line=dict(color=COR_ESCURA, width=3),
                   marker=dict(size=8)),
        secondary_y=True,
    )
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=40, b=40), height=400,
    )
    fig.update_yaxes(title_text="Gasto Marketing (R$)", secondary_y=False)
    fig.update_yaxes(title_text="Faturamento (R$)", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    # ── Tabela: resumo mensal ──
    st.subheader("Resumo Mensal")
    dados_tabela = []
    for i, m_label in enumerate(meses_labels):
        gasto = gastos_mkt[i]
        fat = faturamentos[i]
        locs = locacoes_list[i]
        roi_m = ((fat / gasto - 1) * 100) if gasto > 0 else 0
        cpa_m = gasto / locs if locs > 0 else 0
        dados_tabela.append({
            "Mês": m_label,
            "Gasto Marketing": _formatar_brl(gasto),
            "Faturamento": _formatar_brl(fat),
            "Locações": locs,
            "ROI": f"{roi_m:.0f}%" if gasto > 0 else "—",
            "Custo/Locação": _formatar_brl(cpa_m) if locs > 0 else "—",
        })
    st.table(dados_tabela)

    st.caption(
        "**ROI** = (Faturamento / Gasto - 1) × 100. "
        "**Custo/Locação** = Gasto total em marketing ÷ nº de locações no mês."
    )


# ══════════════════════════════════════════════
# TAB 2 — Instagram
# ══════════════════════════════════════════════
def _render_instagram():
    st.subheader("📸 Métricas do Instagram")
    st.caption("Registre mensalmente os dados do Instagram Insights para acompanhar a evolução.")

    # ── Formulário de registro mensal ──
    with st.expander("➕ Registrar / Atualizar Métricas do Mês", expanded=False):
        with st.form("form_instagram", clear_on_submit=False):
            hoje = date.today()
            meses_nomes = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
            ]
            col_m, col_a = st.columns(2)
            with col_m:
                ig_mes_num = st.selectbox("Mês", range(1, 13),
                                          index=hoje.month - 1,
                                          format_func=lambda x: meses_nomes[x - 1],
                                          key="ig_mes")
            with col_a:
                ig_ano = st.selectbox("Ano", range(hoje.year - 2, hoje.year + 1),
                                      index=2, key="ig_ano")

            mes_str = f"{ig_ano}-{ig_mes_num:02d}"

            # Preencher com dados existentes se houver
            existente = get_instagram_metrica(mes_str)

            col1, col2 = st.columns(2)
            with col1:
                seguidores = st.number_input(
                    "Total de seguidores (no fim do mês)",
                    min_value=0, step=1,
                    value=existente["seguidores"] if existente else 0,
                    key="ig_seg",
                )
                alcance = st.number_input(
                    "Contas alcançadas no mês",
                    min_value=0, step=100,
                    value=existente["alcance"] if existente else 0,
                    key="ig_alcance",
                    help="Disponível em Instagram Insights > Contas alcançadas",
                )
                visitas = st.number_input(
                    "Visitas ao perfil",
                    min_value=0, step=10,
                    value=existente["visitas_perfil"] if existente else 0,
                    key="ig_visitas",
                )
            with col2:
                novos = st.number_input(
                    "Novos seguidores no mês",
                    min_value=0, step=1,
                    value=existente["seguidores_novos"] if existente else 0,
                    key="ig_novos",
                )
                impressoes = st.number_input(
                    "Impressões no mês",
                    min_value=0, step=100,
                    value=existente["impressoes"] if existente else 0,
                    key="ig_impressoes",
                    help="Número total de vezes que seu conteúdo foi exibido",
                )
                cliques = st.number_input(
                    "Cliques no link (bio/stories)",
                    min_value=0, step=1,
                    value=existente["cliques_link"] if existente else 0,
                    key="ig_cliques",
                )

            obs = st.text_area("Observações",
                               value=existente["observacoes"] or "" if existente else "",
                               key="ig_obs",
                               placeholder="Ex: Campanha de Natal ativa, novo Reels viral...")

            if st.form_submit_button("💾 Salvar Métricas", type="primary"):
                salvar_instagram_metrica(
                    mes_str, seguidores, novos, alcance,
                    impressoes, visitas, cliques, obs,
                )
                st.success(f"Métricas de {meses_nomes[ig_mes_num - 1]}/{ig_ano} salvas!")
                st.rerun()

    # ── Métricas atuais (cards) ──
    metricas = listar_instagram_metricas()
    if not metricas:
        st.info("Nenhuma métrica registrada ainda. Use o formulário acima para começar.")
        return

    ultimo = metricas[0]  # Mais recente
    anterior = metricas[1] if len(metricas) > 1 else None

    st.markdown(f"### Último registro: {_mes_label(ultimo['mes'])}")

    c1, c2, c3 = st.columns(3)
    with c1:
        delta_seg = ultimo["seguidores"] - anterior["seguidores"] if anterior else None
        st.metric("Seguidores", f"{ultimo['seguidores']:,}".replace(",", "."),
                  delta=f"+{delta_seg}" if delta_seg and delta_seg > 0 else (str(delta_seg) if delta_seg else None))
    with c2:
        st.metric("Novos Seguidores", f"+{ultimo['seguidores_novos']}")
    with c3:
        taxa_cresc = (ultimo["seguidores_novos"] / anterior["seguidores"] * 100) if anterior and anterior["seguidores"] > 0 else 0
        st.metric("Taxa de Crescimento", f"{taxa_cresc:.1f}%" if anterior else "—")

    c4, c5, c6 = st.columns(3)
    with c4:
        st.metric("Alcance", f"{ultimo['alcance']:,}".replace(",", "."))
    with c5:
        st.metric("Impressões", f"{ultimo['impressoes']:,}".replace(",", "."))
    with c6:
        st.metric("Visitas ao Perfil", f"{ultimo['visitas_perfil']:,}".replace(",", "."))

    # ── Taxa de conversão estimada ──
    gasto_mkt_ultimo = gastos_marketing_mes(ultimo["mes"])
    n_loc_ultimo = num_locacoes_mes(ultimo["mes"])

    st.markdown("---")
    st.subheader("Indicadores de Conversão")

    c7, c8, c9, c10 = st.columns(4)
    with c7:
        taxa_clique = (ultimo["cliques_link"] / ultimo["alcance"] * 100) if ultimo["alcance"] > 0 else 0
        st.metric("Taxa de Clique", f"{taxa_clique:.2f}%",
                  help="Cliques no link ÷ Alcance")
    with c8:
        conv_visita = (n_loc_ultimo / ultimo["visitas_perfil"] * 100) if ultimo["visitas_perfil"] > 0 else 0
        st.metric("Conversão Visita→Locação", f"{conv_visita:.1f}%",
                  help="Locações do mês ÷ Visitas ao perfil")
    with c9:
        custo_seg = gasto_mkt_ultimo / ultimo["seguidores_novos"] if ultimo["seguidores_novos"] > 0 else 0
        st.metric("Custo por Seguidor", _formatar_brl(custo_seg) if ultimo["seguidores_novos"] > 0 else "—",
                  help="Gasto em marketing ÷ Novos seguidores")
    with c10:
        st.metric("Cliques no Link", f"{ultimo['cliques_link']}")

    # ── Gráfico: Evolução de seguidores + gasto marketing ──
    st.markdown("---")
    st.subheader("Evolução de Seguidores vs Investimento em Marketing")

    meses_ig = [dict(m) for m in metricas]
    meses_ig.reverse()  # Cronológico

    if len(meses_ig) >= 2:
        labels = [_mes_label(m["mes"]) for m in meses_ig]
        seg_vals = [m["seguidores"] for m in meses_ig]
        novos_vals = [m["seguidores_novos"] for m in meses_ig]
        gastos_vals = [gastos_marketing_mes(m["mes"]) for m in meses_ig]

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(name="Seguidores", x=labels, y=seg_vals,
                       mode="lines+markers+text", text=seg_vals, textposition="top center",
                       line=dict(color=COR_INSTAGRAM, width=3),
                       marker=dict(size=10)),
            secondary_y=False,
        )
        fig.add_trace(
            go.Bar(name="Gasto Marketing", x=labels, y=gastos_vals,
                   marker_color=COR_CLARA, opacity=0.5),
            secondary_y=True,
        )

        fig.update_layout(
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=40), height=420,
        )
        fig.update_yaxes(title_text="Seguidores", secondary_y=False)
        fig.update_yaxes(title_text="Gasto Marketing (R$)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        # ── Gráfico: Alcance e Impressões ──
        alcance_vals = [m["alcance"] for m in meses_ig]
        impressoes_vals = [m["impressoes"] for m in meses_ig]

        if any(v > 0 for v in alcance_vals) or any(v > 0 for v in impressoes_vals):
            st.subheader("Alcance e Impressões")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(name="Alcance", x=labels, y=alcance_vals,
                                  marker_color=COR_ESCURA))
            fig2.add_trace(go.Bar(name="Impressões", x=labels, y=impressoes_vals,
                                  marker_color=COR_CLARA))
            fig2.update_layout(
                barmode="group", height=350,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                margin=dict(l=20, r=20, t=40, b=40),
            )
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Registre pelo menos 2 meses de métricas para ver os gráficos de evolução.")

    # ── Histórico completo ──
    st.markdown("---")
    st.subheader("Histórico de Métricas")

    dados_hist = []
    for m in metricas:
        dados_hist.append({
            "Mês": _mes_label(m["mes"]),
            "Seguidores": f"{m['seguidores']:,}".replace(",", "."),
            "Novos": f"+{m['seguidores_novos']}",
            "Alcance": f"{m['alcance']:,}".replace(",", "."),
            "Impressões": f"{m['impressoes']:,}".replace(",", "."),
            "Visitas": f"{m['visitas_perfil']:,}".replace(",", "."),
            "Cliques": m["cliques_link"],
        })
    st.table(dados_hist)

    # Excluir registro
    with st.expander("🗑️ Excluir registro de métricas"):
        opcoes_del = [f"{_mes_label(m['mes'])} ({m['mes']})" for m in metricas]
        if opcoes_del:
            sel_del = st.selectbox("Selecione o mês para excluir", opcoes_del, key="ig_del_sel")
            mes_del = sel_del.split("(")[1].rstrip(")")
            confirmar = st.checkbox(f"Confirmar exclusão de {sel_del}", key="ig_del_conf")
            if confirmar:
                if st.button("🗑️ Excluir", key="ig_del_btn"):
                    excluir_instagram_metrica(mes_del)
                    st.success("Registro excluído!")
                    st.rerun()


# ══════════════════════════════════════════════
# TAB 3 — Campanhas
# ══════════════════════════════════════════════
def _render_campanhas():
    st.subheader("🎯 Campanhas de Marketing")
    st.caption("Registre ações específicas: tráfego pago, flyers, parcerias, etc.")

    TIPOS_CAMPANHA = [
        "Tráfego Pago (Instagram)",
        "Tráfego Pago (Google)",
        "Material Impresso (Flyers/Panfletos)",
        "Adesivos/Identidade Visual",
        "Parceria/Indicação",
        "Outro",
    ]

    # ── Nova campanha ──
    with st.expander("➕ Nova Campanha / Ação de Marketing", expanded=False):
        with st.form("form_nova_campanha", clear_on_submit=True):
            nome = st.text_input("Nome da campanha/ação", placeholder="Ex: Campanha Instagram Março")
            tipo = st.selectbox("Tipo", TIPOS_CAMPANHA)

            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input("Data de início", value=date.today())
                investimento = st.number_input("Investimento (R$)", min_value=0.0, step=10.0, format="%.2f")
            with col2:
                data_fim = st.date_input("Data de término (opcional)", value=None)
                alcance_est = st.number_input("Alcance estimado (pessoas)", min_value=0, step=100)

            locacoes_ger = st.number_input(
                "Locações geradas por esta campanha (se souber)", min_value=0, step=1,
                help="Preencha se conseguir rastrear quantas locações vieram desta ação",
            )
            obs = st.text_area("Observações", placeholder="Público-alvo, estratégia, resultados...")

            if st.form_submit_button("💾 Salvar Campanha", type="primary"):
                if not nome.strip():
                    st.error("Informe o nome da campanha.")
                elif investimento <= 0:
                    st.error("Informe o valor do investimento.")
                else:
                    criar_campanha(
                        nome.strip(), tipo,
                        data_inicio.isoformat(),
                        data_fim.isoformat() if data_fim else None,
                        investimento, alcance_est, locacoes_ger, obs,
                    )
                    st.success(f"Campanha '{nome.strip()}' registrada!")
                    st.rerun()

    # ── Listagem de campanhas ──
    campanhas = listar_campanhas()

    if not campanhas:
        st.info("Nenhuma campanha registrada.")
        return

    # KPIs de campanhas
    total_investido = sum(c["investimento"] for c in campanhas)
    total_locacoes_ger = sum(c["locacoes_geradas"] or 0 for c in campanhas)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Investido", _formatar_brl(total_investido))
    with c2:
        st.metric("Total de Campanhas", len(campanhas))
    with c3:
        cpa_camp = total_investido / total_locacoes_ger if total_locacoes_ger > 0 else 0
        st.metric("CPA Médio (Campanhas)", _formatar_brl(cpa_camp) if total_locacoes_ger > 0 else "—",
                  help="Custo por aquisição = Investimento ÷ Locações geradas")

    st.markdown("---")

    # Tabela de campanhas
    for camp in campanhas:
        cid = camp["id"]
        status_icon = "🟢" if not camp["data_fim"] or camp["data_fim"] >= date.today().isoformat() else "⚫"

        with st.expander(f"{status_icon} {camp['nome']} — {_formatar_brl(camp['investimento'])}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Tipo:** {camp['tipo']}")
                st.write(f"**Período:** {camp['data_inicio']} a {camp['data_fim'] or 'em andamento'}")
                st.write(f"**Investimento:** {_formatar_brl(camp['investimento'])}")
            with col2:
                st.write(f"**Alcance estimado:** {camp['alcance_estimado']:,}".replace(",", ".") if camp["alcance_estimado"] else "—")
                st.write(f"**Locações geradas:** {camp['locacoes_geradas'] or '—'}")
                if camp["locacoes_geradas"] and camp["locacoes_geradas"] > 0:
                    cpa = camp["investimento"] / camp["locacoes_geradas"]
                    st.write(f"**CPA:** {_formatar_brl(cpa)}")
                if camp["alcance_estimado"] and camp["alcance_estimado"] > 0:
                    cpm = camp["investimento"] / camp["alcance_estimado"] * 1000
                    st.write(f"**CPM:** {_formatar_brl(cpm)}")

            if camp["observacoes"]:
                st.write(f"**Obs:** {camp['observacoes']}")

            # Editar
            with st.form(f"form_edit_camp_{cid}"):
                st.markdown("**Editar campanha**")
                ed_nome = st.text_input("Nome", value=camp["nome"], key=f"ed_cn_{cid}")
                ed_tipo = st.selectbox("Tipo", TIPOS_CAMPANHA,
                                       index=TIPOS_CAMPANHA.index(camp["tipo"]) if camp["tipo"] in TIPOS_CAMPANHA else 5,
                                       key=f"ed_ct_{cid}")
                ec1, ec2 = st.columns(2)
                with ec1:
                    ed_inicio = st.date_input("Início",
                                              value=datetime.strptime(camp["data_inicio"], "%Y-%m-%d").date(),
                                              key=f"ed_ci_{cid}")
                    ed_invest = st.number_input("Investimento (R$)", min_value=0.0, step=10.0,
                                                value=float(camp["investimento"]), format="%.2f",
                                                key=f"ed_cv_{cid}")
                with ec2:
                    ed_fim = st.date_input("Término",
                                           value=datetime.strptime(camp["data_fim"], "%Y-%m-%d").date() if camp["data_fim"] else None,
                                           key=f"ed_cf_{cid}")
                    ed_alcance = st.number_input("Alcance", min_value=0, step=100,
                                                  value=camp["alcance_estimado"] or 0, key=f"ed_ca_{cid}")
                ed_locacoes = st.number_input("Locações geradas", min_value=0, step=1,
                                               value=camp["locacoes_geradas"] or 0, key=f"ed_cl_{cid}")
                ed_obs = st.text_area("Observações", value=camp["observacoes"] or "", key=f"ed_co_{cid}")

                if st.form_submit_button("💾 Salvar Alterações"):
                    atualizar_campanha(
                        cid, ed_nome.strip(), ed_tipo,
                        ed_inicio.isoformat(),
                        ed_fim.isoformat() if ed_fim else None,
                        ed_invest, ed_alcance, ed_locacoes, ed_obs,
                    )
                    st.success("Campanha atualizada!")
                    st.rerun()

            # Excluir
            conf_del = st.checkbox("Confirmar exclusão", key=f"conf_dc_{cid}")
            if conf_del:
                if st.button("🗑️ Excluir Campanha", key=f"del_c_{cid}"):
                    excluir_campanha(cid)
                    st.success("Campanha excluída!")
                    st.rerun()
