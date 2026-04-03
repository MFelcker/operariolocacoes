"""
Módulo Manutenção — registro e acompanhamento de manutenções dos equipamentos.
"""
import streamlit as st
from datetime import date, datetime

from database import (
    get_config,
    listar_equipamentos,
    listar_manutencoes,
    criar_manutencao,
    atualizar_manutencao,
    excluir_manutencao,
)

ITENS_POR_PAGINA = 20


def _formatar_brl(valor):
    """Formata valor como R$ X.XXX,XX."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _gasto_manutencao_mes_atual():
    """Soma dos custos de manutenções no mês corrente."""
    mes_atual = date.today().strftime("%Y-%m")
    registros = listar_manutencoes()
    total = 0.0
    for r in registros:
        if r["data"] and r["data"][:7] == mes_atual:
            total += r["custo"]
    return total


def render():
    st.title("🔧 Manutenção")

    equipamentos = listar_equipamentos()
    mapa_equip = {e["id"]: e["nome"] for e in equipamentos}

    # ──────────────────────────────────────────
    # 1. Reserva mensal de manutenção
    # ──────────────────────────────────────────
    reserva = float(get_config("reserva_manutencao", "100.00"))
    gasto_mes = _gasto_manutencao_mes_atual()

    st.subheader("Reserva Mensal de Manutenção")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Reserva Configurada", _formatar_brl(reserva))
    with c2:
        st.metric("Gasto no Mês Atual", _formatar_brl(gasto_mes))
    with c3:
        saldo = reserva - gasto_mes
        st.metric("Saldo", _formatar_brl(saldo))
        if saldo < 0:
            st.warning("⚠️ Gastos excederam a reserva mensal!")
        else:
            st.success("✅ Dentro da reserva.")

    st.markdown("---")

    # ──────────────────────────────────────────
    # 2. Nova manutenção
    # ──────────────────────────────────────────
    with st.expander("➕ Registrar Nova Manutenção"):
        if not equipamentos:
            st.info("Nenhum equipamento cadastrado. Cadastre em Configurações.")
        else:
            with st.form("form_nova_manutencao", clear_on_submit=True):
                opcoes_equip = {e["id"]: e["nome"] for e in equipamentos}
                equip_ids = list(opcoes_equip.keys())
                equip_nomes = list(opcoes_equip.values())

                equip_sel = st.selectbox(
                    "Equipamento", equip_ids, format_func=lambda x: opcoes_equip[x]
                )
                data_m = st.date_input("Data", value=date.today())
                tipo_servico = st.text_input(
                    "Tipo de Serviço",
                    placeholder="Ex: Troca de filtro, Bocal, Rodinhas",
                )
                custo = st.number_input("Custo (R$)", min_value=0.0, step=0.01, format="%.2f")
                obs = st.text_area("Observações", placeholder="Detalhes adicionais...")

                if st.form_submit_button("💾 Salvar Manutenção"):
                    if not tipo_servico.strip():
                        st.error("Informe o tipo de serviço.")
                    elif custo <= 0:
                        st.error("Informe um custo válido.")
                    else:
                        criar_manutencao(equip_sel, data_m.isoformat(), tipo_servico.strip(), custo, obs.strip())
                        st.success("Manutenção registrada com sucesso!")
                        st.rerun()

    st.markdown("---")

    # ──────────────────────────────────────────
    # 3. Histórico de manutenções com filtros
    # ──────────────────────────────────────────
    st.subheader("Histórico de Manutenções")

    filtro_equip_id = None
    if equipamentos:
        opcoes_filtro = [("", "Todos os equipamentos")] + [(e["id"], e["nome"]) for e in equipamentos]
        filtro_sel = st.selectbox(
            "Filtrar por equipamento",
            [o[0] for o in opcoes_filtro],
            format_func=lambda x: dict(opcoes_filtro)[x],
            key="filtro_hist_equip",
        )
        if filtro_sel != "":
            filtro_equip_id = filtro_sel

    registros = listar_manutencoes(equipamento_id=filtro_equip_id)

    if not registros:
        st.info("Nenhuma manutenção encontrada.")
    else:
        # Paginação
        total_registros = len(registros)
        total_paginas = max(1, (total_registros + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)

        if "pag_manutencao" not in st.session_state:
            st.session_state["pag_manutencao"] = 1
        pagina = st.number_input(
            "Página",
            min_value=1,
            max_value=total_paginas,
            value=st.session_state["pag_manutencao"],
            step=1,
            key="pag_manut_input",
        )
        st.session_state["pag_manutencao"] = pagina

        inicio = (pagina - 1) * ITENS_POR_PAGINA
        fim = inicio + ITENS_POR_PAGINA
        pagina_registros = registros[inicio:fim]

        st.caption(f"Exibindo {inicio + 1}–{min(fim, total_registros)} de {total_registros} registros")

        for reg in pagina_registros:
            nome_equip = reg["equipamento_nome"]
            with st.container():
                cols = st.columns([2, 2, 2, 2, 2, 1, 1])
                cols[0].write(f"**Data:** {reg['data']}")
                cols[1].write(f"**Máquina:** {nome_equip}")
                cols[2].write(f"**Tipo:** {reg['tipo_servico']}")
                cols[3].write(f"**Custo:** {_formatar_brl(reg['custo'])}")
                cols[4].write(f"**Obs:** {reg['observacoes'] or '—'}")

                # Editar
                if cols[5].button("✏️", key=f"edit_m_{reg['id']}"):
                    st.session_state[f"editando_manut_{reg['id']}"] = True

                # Excluir
                if cols[6].button("🗑️", key=f"del_m_{reg['id']}"):
                    excluir_manutencao(reg["id"])
                    st.success("Manutenção excluída.")
                    st.rerun()

                # Formulário de edição inline
                if st.session_state.get(f"editando_manut_{reg['id']}", False):
                    with st.form(f"form_edit_manut_{reg['id']}"):
                        st.markdown(f"**Editando manutenção #{reg['id']}**")
                        opcoes_equip_edit = {e["id"]: e["nome"] for e in equipamentos}
                        equip_ids_edit = list(opcoes_equip_edit.keys())

                        idx_atual = equip_ids_edit.index(reg["equipamento_id"]) if reg["equipamento_id"] in equip_ids_edit else 0
                        ed_equip = st.selectbox(
                            "Equipamento",
                            equip_ids_edit,
                            index=idx_atual,
                            format_func=lambda x: opcoes_equip_edit[x],
                            key=f"ed_equip_{reg['id']}",
                        )
                        ed_data = st.date_input(
                            "Data",
                            value=datetime.strptime(reg["data"], "%Y-%m-%d").date(),
                            key=f"ed_data_{reg['id']}",
                        )
                        ed_tipo = st.text_input("Tipo de Serviço", value=reg["tipo_servico"], key=f"ed_tipo_{reg['id']}")
                        ed_custo = st.number_input(
                            "Custo (R$)", min_value=0.0, value=float(reg["custo"]), step=0.01,
                            format="%.2f", key=f"ed_custo_{reg['id']}",
                        )
                        ed_obs = st.text_area("Observações", value=reg["observacoes"] or "", key=f"ed_obs_{reg['id']}")

                        col_save, col_cancel = st.columns(2)
                        if col_save.form_submit_button("💾 Salvar"):
                            atualizar_manutencao(
                                reg["id"], ed_equip, ed_data.isoformat(),
                                ed_tipo.strip(), ed_custo, ed_obs.strip(),
                            )
                            st.session_state[f"editando_manut_{reg['id']}"] = False
                            st.success("Manutenção atualizada!")
                            st.rerun()
                        if col_cancel.form_submit_button("Cancelar"):
                            st.session_state[f"editando_manut_{reg['id']}"] = False
                            st.rerun()

                st.markdown("---")

    # ──────────────────────────────────────────
    # 4. Histórico por máquina
    # ──────────────────────────────────────────
    st.subheader("Histórico por Máquina")

    if not equipamentos:
        st.info("Nenhum equipamento cadastrado.")
    else:
        opcoes_maq = {e["id"]: e["nome"] for e in equipamentos}
        maq_sel = st.selectbox(
            "Selecione o equipamento",
            list(opcoes_maq.keys()),
            format_func=lambda x: opcoes_maq[x],
            key="hist_por_maquina",
        )

        registros_maq = listar_manutencoes(equipamento_id=maq_sel)
        if not registros_maq:
            st.info(f"Nenhuma manutenção registrada para {opcoes_maq[maq_sel]}.")
        else:
            dados_tabela = []
            for r in registros_maq:
                dados_tabela.append({
                    "Data": r["data"],
                    "Tipo": r["tipo_servico"],
                    "Custo": _formatar_brl(r["custo"]),
                    "Observações": r["observacoes"] or "—",
                })
            st.table(dados_tabela)

            total_custo = sum(r["custo"] for r in registros_maq)
            st.markdown(f"**Total gasto com {opcoes_maq[maq_sel]}:** {_formatar_brl(total_custo)}")
