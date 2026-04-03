"""
Módulo de Locações — CRUD completo de locações de equipamentos.
"""
from datetime import date, datetime, timedelta
import math
import streamlit as st
from database import (
    listar_clientes,
    listar_equipamentos,
    listar_locacoes,
    criar_locacao,
    atualizar_locacao,
    excluir_locacao,
    verificar_conflito,
    get_config,
)


def _calcular_sabao_extra(sabao_ml: int) -> float:
    """Primeiros 500 ml são gratuitos; excedente cobrado a R$15 por 500 ml."""
    preco_por_500 = float(get_config("valor_produto_extra", "15"))
    excedente = max(0, sabao_ml - 500)
    return math.ceil(excedente / 500) * preco_por_500


def _formatar_brl(valor) -> str:
    """Formata um número como moeda brasileira."""
    if valor is None:
        return "R$ 0,00"
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_date(value):
    """Converte string ISO ou date para date."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _calcular_total(loc) -> float:
    """Calcula valor total da locação: diária x dias + sabão extra."""
    data_saida = _parse_date(loc["data_saida"])
    data_fim = _parse_date(loc["data_retorno_efetiva"]) or _parse_date(loc["data_retorno_prevista"])
    if data_saida and data_fim:
        dias = (data_fim - data_saida).days + 1
        dias = max(dias, 1)
    else:
        dias = 1
    diaria = float(loc["valor_diaria"] or 0)
    sabao = float(loc["valor_sabao_extra"] or 0)
    return diaria * dias + sabao


# ──────────────────────────────────────────────
# Seletor de sabão reutilizável
# ──────────────────────────────────────────────
def _sabao_input(prefix: str, default_ml: int = 500):
    opcoes = ["500", "1000", "1500", "2000", "Outro"]
    default_str = str(default_ml) if str(default_ml) in opcoes else "Outro"
    escolha = st.selectbox(
        "Quantidade de sabão utilizado (ml)",
        opcoes,
        index=opcoes.index(default_str),
        key=f"{prefix}_sabao_sel",
    )
    if escolha == "Outro":
        sabao_ml = st.number_input(
            "Informe a quantidade (ml)",
            min_value=0,
            step=100,
            value=default_ml if default_str == "Outro" else 0,
            key=f"{prefix}_sabao_custom",
        )
    else:
        sabao_ml = int(escolha)
    return sabao_ml


# ══════════════════════════════════════════════
# RENDER
# ══════════════════════════════════════════════
def render():
    st.header("📦 Locações")

    clientes = listar_clientes()
    equipamentos_todos = listar_equipamentos()
    equipamentos_disp = listar_equipamentos(status="disponivel")

    # ──────────────────────────────────────────
    # 1. Nova Locação
    # ──────────────────────────────────────────
    abrir = st.session_state.get("abrir_nova_locacao", False)
    with st.expander("➕ Nova Locação", expanded=abrir):
        if not clientes:
            st.warning("Nenhum cliente cadastrado. Cadastre um cliente antes de criar uma locação.")
        elif not equipamentos_disp:
            st.warning("Nenhum equipamento disponível no momento.")
        else:
            with st.form("form_nova_locacao"):
                col1, col2 = st.columns(2)
                with col1:
                    cliente_map = {c["nome"]: c["id"] for c in clientes}
                    cliente_nome = st.selectbox("Cliente", list(cliente_map.keys()))
                    data_saida = st.date_input("Data de saída", value=date.today())
                    valor_diaria_padrao = float(get_config("valor_diaria_padrao", "100"))
                    valor_diaria = st.number_input(
                        "Valor da diária (R$)",
                        min_value=0.0,
                        step=10.0,
                        value=valor_diaria_padrao,
                        format="%.2f",
                    )
                with col2:
                    equip_map = {e["nome"]: e["id"] for e in equipamentos_disp}
                    equip_nome = st.selectbox("Equipamento", list(equip_map.keys()))
                    data_retorno_prevista = st.date_input(
                        "Data de retorno prevista", value=date.today() + timedelta(days=7)
                    )

                sabao_ml = _sabao_input("nova")
                valor_sabao_extra = _calcular_sabao_extra(sabao_ml)
                st.info(f"Custo extra de sabão: {_formatar_brl(valor_sabao_extra)}")

                observacoes = st.text_area("Observações", key="nova_obs")

                enviado = st.form_submit_button("💾 Salvar Locação", type="primary")

            if enviado:
                cliente_id = cliente_map[cliente_nome]
                equipamento_id = equip_map[equip_nome]

                conflito = verificar_conflito(equipamento_id, str(data_saida), str(data_retorno_prevista))
                if conflito:
                    st.error(
                        "⚠️ Conflito de datas! Este equipamento já possui uma locação ativa "
                        "no período selecionado. Ajuste as datas ou escolha outro equipamento."
                    )
                else:
                    criar_locacao(
                        cliente_id=cliente_id,
                        equipamento_id=equipamento_id,
                        data_saida=str(data_saida),
                        data_retorno_prevista=str(data_retorno_prevista),
                        valor_diaria=valor_diaria,
                        sabao_ml=sabao_ml,
                        valor_sabao_extra=valor_sabao_extra,
                        observacoes=observacoes,
                    )
                    st.success("✅ Locação criada com sucesso!")
                    st.session_state.pop("abrir_nova_locacao", None)
                    st.rerun()

    # Sempre limpar a flag após renderizar o expander
    st.session_state.pop("abrir_nova_locacao", None)

    # ──────────────────────────────────────────
    # 2. Filtros
    # ──────────────────────────────────────────
    st.subheader("Filtros")
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        mes_filter = st.text_input("Mês (AAAA-MM)", placeholder="2026-04", key="loc_mes")
    with fc2:
        cliente_filter_opts = ["Todos"] + [c["nome"] for c in clientes]
        cliente_filter_nome = st.selectbox("Cliente", cliente_filter_opts, key="loc_cli_filter")
    with fc3:
        equip_filter_opts = ["Todos"] + [e["nome"] for e in equipamentos_todos]
        equip_filter_nome = st.selectbox("Equipamento", equip_filter_opts, key="loc_eq_filter")
    with fc4:
        status_opts = ["Todos", "ativa", "encerrada"]
        status_filter = st.selectbox("Status", status_opts, key="loc_status_filter")

    # Resolver IDs dos filtros
    f_mes = mes_filter if mes_filter else None
    f_cliente_id = None
    if cliente_filter_nome != "Todos":
        for c in clientes:
            if c["nome"] == cliente_filter_nome:
                f_cliente_id = c["id"]
                break
    f_equip_id = None
    if equip_filter_nome != "Todos":
        for e in equipamentos_todos:
            if e["nome"] == equip_filter_nome:
                f_equip_id = e["id"]
                break
    f_status = status_filter if status_filter != "Todos" else None

    locacoes = listar_locacoes(mes=f_mes, cliente_id=f_cliente_id, equipamento_id=f_equip_id, status=f_status)

    # ──────────────────────────────────────────
    # 3. Tabela de Locações
    # ──────────────────────────────────────────
    st.subheader("Locações")

    if not locacoes:
        st.info("Nenhuma locação encontrada com os filtros selecionados.")
        return

    # Paginação
    PAGE_SIZE = 20
    total_pages = max(1, math.ceil(len(locacoes) / PAGE_SIZE))
    page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1, key="loc_page")
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    locacoes_page = locacoes[start:end]

    # Cabeçalho da tabela
    header_cols = st.columns([1, 2, 2, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1])
    headers = ["ID", "Cliente", "Máquina", "Saída", "Ret. Prev.", "Ret. Efet.", "Diária", "Sabão Extra", "Total", "Status"]
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    st.markdown("---")

    # Linhas
    for loc in locacoes_page:
        total_val = _calcular_total(loc)
        data_cols = st.columns([1, 2, 2, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1])
        data_cols[0].write(loc["id"])
        data_cols[1].write(loc["cliente_nome"])
        data_cols[2].write(loc["equipamento_nome"])
        data_cols[3].write(loc["data_saida"] or "—")
        data_cols[4].write(loc["data_retorno_prevista"] or "—")
        data_cols[5].write(loc["data_retorno_efetiva"] or "—")
        data_cols[6].write(_formatar_brl(loc["valor_diaria"]))
        data_cols[7].write(_formatar_brl(loc["valor_sabao_extra"]))
        data_cols[8].write(_formatar_brl(total_val))
        data_cols[9].write("🟢 Ativa" if loc["status"] == "ativa" else "🔴 Encerrada")

        # ──────────────────────────────────────
        # 4. Editar / Excluir
        # ──────────────────────────────────────
        with st.expander(f"✏️ Gerenciar locação #{loc['id']}"):
            with st.form(f"form_edit_{loc['id']}"):
                ec1, ec2 = st.columns(2)
                with ec1:
                    edit_cliente_map = {c["nome"]: c["id"] for c in clientes}
                    edit_cliente_names = list(edit_cliente_map.keys())
                    cur_cli_idx = 0
                    for i, name in enumerate(edit_cliente_names):
                        if edit_cliente_map[name] == loc["cliente_id"]:
                            cur_cli_idx = i
                            break
                    edit_cliente = st.selectbox(
                        "Cliente", edit_cliente_names, index=cur_cli_idx,
                        key=f"edit_cli_{loc['id']}"
                    )

                    edit_data_saida = st.date_input(
                        "Data de saída",
                        value=_parse_date(loc["data_saida"]),
                        key=f"edit_ds_{loc['id']}",
                    )

                    edit_diaria = st.number_input(
                        "Valor da diária (R$)",
                        min_value=0.0, step=10.0,
                        value=float(loc["valor_diaria"] or 0),
                        format="%.2f",
                        key=f"edit_vd_{loc['id']}",
                    )

                with ec2:
                    edit_equip_map = {e["nome"]: e["id"] for e in equipamentos_todos}
                    edit_equip_names = list(edit_equip_map.keys())
                    cur_eq_idx = 0
                    for i, name in enumerate(edit_equip_names):
                        if edit_equip_map[name] == loc["equipamento_id"]:
                            cur_eq_idx = i
                            break
                    edit_equip = st.selectbox(
                        "Equipamento", edit_equip_names, index=cur_eq_idx,
                        key=f"edit_eq_{loc['id']}"
                    )

                    edit_data_ret_prev = st.date_input(
                        "Data retorno prevista",
                        value=_parse_date(loc["data_retorno_prevista"]),
                        key=f"edit_drp_{loc['id']}",
                    )

                edit_sabao = _sabao_input(f"edit_{loc['id']}", default_ml=int(loc["sabao_ml"] or 500))
                edit_sabao_extra = _calcular_sabao_extra(edit_sabao)
                st.info(f"Custo extra de sabão: {_formatar_brl(edit_sabao_extra)}")

                status_opcoes = ["ativa", "encerrada"]
                cur_status_idx = status_opcoes.index(loc["status"]) if loc["status"] in status_opcoes else 0
                edit_status = st.selectbox(
                    "Status", status_opcoes, index=cur_status_idx,
                    key=f"edit_st_{loc['id']}"
                )

                # Campos adicionais quando encerrada
                edit_data_ret_efetiva = None
                edit_dano_descricao = ""
                edit_dano_valor = 0.0

                if edit_status == "encerrada":
                    st.markdown("---")
                    st.markdown("**Dados de encerramento**")
                    default_ret_efetiva = _parse_date(loc["data_retorno_efetiva"]) or date.today()
                    edit_data_ret_efetiva = st.date_input(
                        "Data retorno efetiva",
                        value=default_ret_efetiva,
                        key=f"edit_dre_{loc['id']}",
                    )
                    edit_dano_descricao = st.text_input(
                        "Descrição do dano",
                        value=loc["dano_descricao"] or "",
                        key=f"edit_dano_d_{loc['id']}",
                    )
                    edit_dano_valor = st.number_input(
                        "Valor do dano (R$)",
                        min_value=0.0, step=10.0,
                        value=float(loc["dano_valor"] or 0),
                        format="%.2f",
                        key=f"edit_dano_v_{loc['id']}",
                    )

                edit_obs = st.text_area(
                    "Observações",
                    value=loc["observacoes"] or "",
                    key=f"edit_obs_{loc['id']}",
                )

                salvar_edit = st.form_submit_button("💾 Salvar Alterações", type="primary")

            if salvar_edit:
                new_equip_id = edit_equip_map[edit_equip]
                conflito = verificar_conflito(
                    new_equip_id,
                    str(edit_data_saida),
                    str(edit_data_ret_prev),
                    excluir_locacao_id=loc["id"],
                )
                if conflito:
                    st.error(
                        "⚠️ Conflito de datas! Este equipamento já possui uma locação ativa "
                        "no período selecionado."
                    )
                else:
                    atualizar_locacao(
                        lid=loc["id"],
                        cliente_id=edit_cliente_map[edit_cliente],
                        equipamento_id=new_equip_id,
                        data_saida=str(edit_data_saida),
                        data_retorno_prevista=str(edit_data_ret_prev),
                        data_retorno_efetiva=str(edit_data_ret_efetiva) if edit_data_ret_efetiva else None,
                        valor_diaria=edit_diaria,
                        sabao_ml=edit_sabao,
                        valor_sabao_extra=edit_sabao_extra,
                        status=edit_status,
                        observacoes=edit_obs,
                        dano_descricao=edit_dano_descricao,
                        dano_valor=edit_dano_valor,
                    )
                    st.success("✅ Locação atualizada com sucesso!")
                    st.rerun()

            # Botão de exclusão (fora do form)
            st.markdown("---")
            del_key = f"confirm_del_{loc['id']}"
            if st.checkbox("Confirmar exclusão desta locação", key=del_key):
                if st.button("🗑️ Excluir Locação", key=f"btn_del_{loc['id']}", type="primary"):
                    excluir_locacao(loc["id"])
                    st.success("✅ Locação excluída com sucesso!")
                    st.rerun()

    st.caption(f"Exibindo página {page} de {total_pages} — Total de {len(locacoes)} locações")
