"""
Módulo Despesas — gestão de despesas gerais e parcelas de equipamento.
"""
import streamlit as st
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from database import (
    listar_despesas,
    criar_despesa,
    atualizar_despesa,
    excluir_despesa,
    listar_parcelas_equipamento,
    criar_parcelas_equipamento,
    listar_parcelas,
    marcar_parcela_paga,
    excluir_parcelas_equipamento,
    listar_equipamentos,
)

# ──────────────────────────────────────────────
# Constantes
# ──────────────────────────────────────────────
CATEGORIAS = {
    "sabao": "Sabão",
    "gasolina": "Gasolina",
    "manutencao": "Manutenção",
    "outros": "Outros",
    "parcelas": "Parcelas",
}

CATEGORIAS_FORM = {
    "sabao": "Compra de Sabão",
    "gasolina": "Gasolina",
    "manutencao": "Manutenção",
    "outros": "Outros",
}

LINHAS_POR_PAGINA = 20


def _formatar_brl(valor):
    """Formata valor como R$ X.XXX,XX."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _nome_categoria(cat):
    """Retorna nome de exibição da categoria."""
    return CATEGORIAS.get(cat, cat)


# ──────────────────────────────────────────────
# Tab 1 — Despesas Gerais
# ──────────────────────────────────────────────
def _render_despesas_gerais():
    # ── Formulário de nova despesa ──
    with st.expander("➕ Nova Despesa", expanded=False):
        with st.form("form_nova_despesa", clear_on_submit=True):
            cat_options = list(CATEGORIAS_FORM.keys())
            cat_labels = list(CATEGORIAS_FORM.values())
            cat_idx = st.selectbox(
                "Categoria",
                range(len(cat_options)),
                format_func=lambda i: cat_labels[i],
            )
            categoria = cat_options[cat_idx]

            descricao = st.text_input("Descrição")
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
            data_desp = st.date_input("Data", value=date.today())

            quantidade_ml = 0
            if categoria == "sabao":
                quantidade_ml = st.number_input(
                    "Quantidade (ml)", min_value=0, step=100, value=0
                )

            submitted = st.form_submit_button("💾 Salvar Despesa")
            if submitted:
                if valor <= 0:
                    st.error("Informe um valor maior que zero.")
                else:
                    criar_despesa(
                        categoria,
                        descricao,
                        valor,
                        data_desp.isoformat(),
                        int(quantidade_ml),
                    )
                    st.success("Despesa registrada com sucesso!")
                    st.rerun()

    # ── Filtros ──
    st.subheader("Filtros")
    col_mes, col_cat = st.columns(2)
    with col_mes:
        filtro_mes = st.text_input(
            "Mês (AAAA-MM)",
            value=date.today().strftime("%Y-%m"),
            placeholder="2025-01",
            key="filtro_mes_desp",
        )
    with col_cat:
        opcoes_cat = ["Todas"] + list(CATEGORIAS_FORM.values())
        chaves_cat = [None] + list(CATEGORIAS_FORM.keys())
        sel_cat_idx = st.selectbox(
            "Categoria",
            range(len(opcoes_cat)),
            format_func=lambda i: opcoes_cat[i],
            key="filtro_cat_desp",
        )
        filtro_cat = chaves_cat[sel_cat_idx]

    # ── Listagem ──
    despesas = listar_despesas(
        mes=filtro_mes if filtro_mes else None,
        categoria=filtro_cat,
    )

    if not despesas:
        st.info("Nenhuma despesa encontrada para os filtros selecionados.")
        return

    # Paginação
    total = len(despesas)
    total_paginas = max(1, (total + LINHAS_POR_PAGINA - 1) // LINHAS_POR_PAGINA)
    pagina_key = "pag_despesas_gerais"
    if pagina_key not in st.session_state:
        st.session_state[pagina_key] = 1
    pagina_atual = st.session_state[pagina_key]
    if pagina_atual > total_paginas:
        pagina_atual = total_paginas
        st.session_state[pagina_key] = pagina_atual

    inicio = (pagina_atual - 1) * LINHAS_POR_PAGINA
    fim = min(inicio + LINHAS_POR_PAGINA, total)
    despesas_pagina = despesas[inicio:fim]

    st.markdown(f"**Exibindo {inicio + 1}–{fim} de {total} despesas**")

    # Tabela
    for d in despesas_pagina:
        did = d["id"]
        col_data, col_cat, col_desc, col_val, col_ml, col_acoes = st.columns(
            [1.2, 1.2, 2, 1.2, 0.8, 1.5]
        )
        col_data.write(d["data"])
        col_cat.write(_nome_categoria(d["categoria"]))
        col_desc.write(d["descricao"] or "—")
        col_val.write(_formatar_brl(d["valor"]))
        col_ml.write(f'{d["quantidade_ml"]} ml' if d["quantidade_ml"] else "—")

        with col_acoes:
            c_edit, c_del = st.columns(2)
            if c_edit.button("✏️", key=f"edit_desp_{did}"):
                st.session_state[f"editando_desp_{did}"] = True
            if c_del.button("🗑️", key=f"del_desp_{did}"):
                excluir_despesa(did)
                st.success("Despesa excluída.")
                st.rerun()

        # Formulário de edição inline
        if st.session_state.get(f"editando_desp_{did}", False):
            with st.form(f"form_edit_desp_{did}"):
                st.markdown(f"**Editando despesa #{did}**")
                cat_options_e = list(CATEGORIAS_FORM.keys())
                cat_labels_e = list(CATEGORIAS_FORM.values())
                cur_cat = d["categoria"]
                cur_idx = cat_options_e.index(cur_cat) if cur_cat in cat_options_e else 0
                cat_idx_e = st.selectbox(
                    "Categoria",
                    range(len(cat_options_e)),
                    index=cur_idx,
                    format_func=lambda i: cat_labels_e[i],
                    key=f"cat_edit_{did}",
                )
                cat_edit = cat_options_e[cat_idx_e]

                desc_edit = st.text_input("Descrição", value=d["descricao"] or "", key=f"desc_edit_{did}")
                val_edit = st.number_input(
                    "Valor (R$)", min_value=0.0, step=0.01, format="%.2f",
                    value=float(d["valor"]), key=f"val_edit_{did}",
                )
                data_edit = st.date_input(
                    "Data",
                    value=datetime.strptime(d["data"], "%Y-%m-%d").date() if isinstance(d["data"], str) else d["data"],
                    key=f"data_edit_{did}",
                )

                ml_edit = 0
                if cat_edit == "sabao":
                    ml_edit = st.number_input(
                        "Quantidade (ml)", min_value=0, step=100,
                        value=int(d["quantidade_ml"]) if d["quantidade_ml"] else 0,
                        key=f"ml_edit_{did}",
                    )

                col_salvar, col_cancelar = st.columns(2)
                salvar = col_salvar.form_submit_button("💾 Salvar")
                cancelar = col_cancelar.form_submit_button("❌ Cancelar")

                if salvar:
                    if val_edit <= 0:
                        st.error("Informe um valor maior que zero.")
                    else:
                        atualizar_despesa(
                            did, cat_edit, desc_edit, val_edit,
                            data_edit.isoformat(), int(ml_edit),
                        )
                        st.session_state[f"editando_desp_{did}"] = False
                        st.success("Despesa atualizada com sucesso!")
                        st.rerun()
                if cancelar:
                    st.session_state[f"editando_desp_{did}"] = False
                    st.rerun()

    # Controles de paginação
    if total_paginas > 1:
        st.markdown("---")
        col_ant, col_info, col_prox = st.columns([1, 2, 1])
        with col_ant:
            if st.button("⬅️ Anterior", disabled=(pagina_atual <= 1), key="pag_ant_desp"):
                st.session_state[pagina_key] = pagina_atual - 1
                st.rerun()
        with col_info:
            st.markdown(f"<p style='text-align:center'>Página {pagina_atual} de {total_paginas}</p>", unsafe_allow_html=True)
        with col_prox:
            if st.button("Próxima ➡️", disabled=(pagina_atual >= total_paginas), key="pag_prox_desp"):
                st.session_state[pagina_key] = pagina_atual + 1
                st.rerun()


# ──────────────────────────────────────────────
# Tab 2 — Parcelas de Equipamento
# ──────────────────────────────────────────────
def _render_parcelas_equipamento():
    equipamentos = listar_equipamentos()

    # ── Formulário de novo parcelamento ──
    with st.expander("➕ Novo Parcelamento de Equipamento", expanded=False):
        if not equipamentos:
            st.warning("Nenhum equipamento cadastrado. Cadastre um equipamento primeiro.")
        else:
            with st.form("form_novo_parcelamento", clear_on_submit=True):
                equip_nomes = [e["nome"] for e in equipamentos]
                equip_ids = [e["id"] for e in equipamentos]
                sel_equip_idx = st.selectbox(
                    "Equipamento",
                    range(len(equip_nomes)),
                    format_func=lambda i: equip_nomes[i],
                )
                equip_id = equip_ids[sel_equip_idx]
                nome_equip = equip_nomes[sel_equip_idx]

                st.text_input("Nome do equipamento", value=nome_equip, disabled=True)

                valor_total = st.number_input(
                    "Valor total (R$)", min_value=0.01, step=0.01, format="%.2f"
                )
                num_parcelas = st.number_input(
                    "Número de parcelas", min_value=1, step=1, value=12
                )
                data_inicio = st.date_input("Data de início", value=date.today())

                # Preview
                if valor_total > 0 and num_parcelas > 0:
                    valor_parc = round(valor_total / num_parcelas, 2)
                    dt_quitacao = data_inicio + relativedelta(months=int(num_parcelas) - 1)
                    st.info(
                        f"Valor de cada parcela: **{_formatar_brl(valor_parc)}** | "
                        f"Previsão de quitação: **{dt_quitacao.strftime('%d/%m/%Y')}**"
                    )

                submitted = st.form_submit_button("💾 Criar Parcelamento")
                if submitted:
                    if valor_total <= 0:
                        st.error("Informe um valor total maior que zero.")
                    elif num_parcelas < 1:
                        st.error("Informe ao menos 1 parcela.")
                    else:
                        criar_parcelas_equipamento(
                            equip_id,
                            nome_equip,
                            valor_total,
                            int(num_parcelas),
                            data_inicio.isoformat(),
                        )
                        st.success("Parcelamento criado com sucesso!")
                        st.rerun()

    # ── Listagem de parcelamentos ──
    planos = listar_parcelas_equipamento()

    if not planos:
        st.info("Nenhum parcelamento de equipamento cadastrado.")
        return

    st.subheader("Parcelamentos Cadastrados")

    for pe in planos:
        pe_id = pe["id"]
        dt_inicio = pe["data_inicio"]
        num_p = pe["num_parcelas"]

        # Calcular previsão de quitação
        if isinstance(dt_inicio, str):
            dt_ini_obj = datetime.strptime(dt_inicio, "%Y-%m-%d").date()
        else:
            dt_ini_obj = dt_inicio
        dt_quitacao = dt_ini_obj + relativedelta(months=num_p - 1)

        col_info, col_del = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"**{pe['nome_equipamento']}** — "
                f"Valor Total: {_formatar_brl(pe['valor_total'])} | "
                f"Parcelas: {num_p} | "
                f"Início: {dt_ini_obj.strftime('%d/%m/%Y')} | "
                f"Previsão de Quitação: {dt_quitacao.strftime('%d/%m/%Y')}"
            )
        with col_del:
            if st.button("🗑️ Excluir", key=f"del_pe_{pe_id}"):
                excluir_parcelas_equipamento(pe_id)
                st.success("Parcelamento excluído com sucesso!")
                st.rerun()

        # Parcelas individuais
        with st.expander(f"📋 Parcelas — {pe['nome_equipamento']}", expanded=False):
            parcelas = listar_parcelas(parcela_equip_id=pe_id)
            if not parcelas:
                st.info("Nenhuma parcela encontrada.")
            else:
                for p in parcelas:
                    pid = p["id"]
                    dt_venc = p["data_vencimento"]
                    if isinstance(dt_venc, str):
                        dt_venc_fmt = datetime.strptime(dt_venc, "%Y-%m-%d").date().strftime("%d/%m/%Y")
                    else:
                        dt_venc_fmt = dt_venc.strftime("%d/%m/%Y")

                    paga = bool(p["paga"])
                    col_num, col_val, col_dt, col_chk = st.columns([0.5, 1.5, 1.5, 1])
                    col_num.write(f"#{p['numero']}")
                    col_val.write(_formatar_brl(p["valor"]))
                    col_dt.write(dt_venc_fmt)
                    with col_chk:
                        novo_estado = st.checkbox(
                            "Paga",
                            value=paga,
                            key=f"chk_parcela_{pid}",
                        )
                        if novo_estado != paga:
                            marcar_parcela_paga(pid, 1 if novo_estado else 0)
                            st.rerun()

        st.markdown("---")


# ──────────────────────────────────────────────
# Render principal
# ──────────────────────────────────────────────
def render():
    st.title("💰 Despesas")

    tab_gerais, tab_parcelas = st.tabs(["Despesas Gerais", "Parcelas de Equipamento"])

    with tab_gerais:
        _render_despesas_gerais()

    with tab_parcelas:
        _render_parcelas_equipamento()
